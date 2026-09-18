from __future__ import annotations

import builtins
import ctypes
import importlib.util
import inspect
import json
from pathlib import Path
import re
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock
import zlib
import base64

import polib

import update_translations


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "addon/globalPlugins/nvda_macro_manager.py"


class _FakeLog:
	def __init__(self):
		self.records = []

	def error(self, message):
		self.records.append(("error", message))

	def debugWarning(self, message):
		self.records.append(("warning", message))


class _BaseGlobalPlugin:
	def terminate(self):
		self.terminated = True


def _script(**_kwargs):
	return lambda function: function


def _install_nvda_stubs(config_path: str):
	messages = []
	focus_object = types.SimpleNamespace(appModule=types.SimpleNamespace(appName="target"))
	app_name_lookups = []

	def get_app_name_from_process_id(process_id):
		app_name_lookups.append(process_id)
		return "target" if process_id == 4242 else None

	addon_handler = types.ModuleType("addonHandler")
	addon_handler.translation = lambda message: message
	builtins._ = lambda message: f"NVDA core: {message}"

	def init_translation():
		caller_frame = inspect.currentframe().f_back
		try:
			caller_frame.f_globals["_"] = addon_handler.translation
		finally:
			del caller_frame

	addon_handler.initTranslation = init_translation
	modules = {
		"addonHandler": addon_handler,
		"api": types.SimpleNamespace(
			copyToClip=lambda _text: True,
			getClipData=lambda: "",
			getFocusObject=lambda: focus_object,
			getForegroundObject=lambda: focus_object,
		),
		"appModuleHandler": types.SimpleNamespace(
			getAppNameFromProcessID=get_app_name_from_process_id,
			lookups=app_name_lookups,
		),
		"core": types.SimpleNamespace(callLater=lambda _delay, callback, *args: callback(*args)),
		"globalPluginHandler": types.SimpleNamespace(GlobalPlugin=_BaseGlobalPlugin),
		"globalVars": types.SimpleNamespace(appArgs=types.SimpleNamespace(configPath=config_path)),
		"gui": types.SimpleNamespace(mainFrame=types.SimpleNamespace()),
		"logHandler": types.SimpleNamespace(log=_FakeLog()),
		"scriptHandler": types.SimpleNamespace(script=_script),
		"ui": types.SimpleNamespace(message=messages.append),
		"winUser": types.SimpleNamespace(
			getForegroundWindow=lambda: 1,
			getWindowThreadProcessID=lambda _hwnd: (4242, 7777),
		),
	}
	wx = types.ModuleType("wx")
	wx.Dialog = type("Dialog", (), {})
	modules["wx"] = wx
	for name, module in modules.items():
		sys.modules[name] = module
	return modules, messages


def _load_addon(config_path: str):
	modules, messages = _install_nvda_stubs(config_path)
	sys.modules.pop("nvda_macro_manager_under_test", None)
	spec = importlib.util.spec_from_file_location("nvda_macro_manager_under_test", MODULE_PATH)
	module = importlib.util.module_from_spec(spec)
	assert spec and spec.loader
	sys.modules[spec.name] = module
	spec.loader.exec_module(module)
	return module, modules, messages


class _FakeUser32:
	def __init__(self, hook=123):
		self.hook = hook
		self.async_keys = set()
		self.sent = []
		self.unhooked = []
		self.fail_send_number = None
		self.send_calls = 0

	def SetWindowsHookExW(self, *_args):
		return self.hook

	def UnhookWindowsHookEx(self, hook):
		self.unhooked.append(hook)
		return 1

	def CallNextHookEx(self, *_args):
		return 77

	def GetAsyncKeyState(self, key):
		return 0x8000 if key in self.async_keys else 0

	def SendInput(self, _count, pointer, _size):
		self.send_calls += 1
		if self.send_calls == self.fail_send_number:
			return 0
		value = ctypes.cast(pointer, ctypes.POINTER(self.input_type)).contents
		self.sent.append((value.ii.ki.wVk, value.ii.ki.dwFlags))
		return 1


class MacroManagerTests(unittest.TestCase):
	def setUp(self):
		self.temp_dir = tempfile.TemporaryDirectory()
		self.addCleanup(self.temp_dir.cleanup)
		self.module, self.stubs, self.messages = _load_addon(self.temp_dir.name)
		self.user32 = _FakeUser32()
		self.user32.input_type = self.module.Input
		self.module.user32 = self.user32

	def _event(self, action="keyDown", vk=65, delay=0.0):
		return {"action": action, "vkCode": vk, "scanCode": 30, "extended": False, "delay": delay}

	def _keyboard_data(self, vk=65, flags=0):
		return self.module.KBDLLHOOKSTRUCT(vkCode=vk, scanCode=30, flags=flags, time=0, dwExtraInfo=0)

	def test_addon_translation_is_not_overwritten_by_nvda_core_translation(self):
		self.assertIs(self.stubs["addonHandler"].translation, self.module._)
		self.assertEqual("Macro Manager", self.module._("Macro Manager"))

	def test_foreground_application_lookup_uses_process_id_not_thread_id(self):
		for app_name in ("audacity", "forge18"):
			with self.subTest(app_name=app_name):
				lookups = []

				def lookup(process_id):
					lookups.append(process_id)
					return app_name if process_id == 4242 else None

				self.stubs["appModuleHandler"].getAppNameFromProcessID = lookup
				self.assertEqual(app_name, self.module.get_foreground_app())
				self.assertEqual([4242], lookups)

	def test_recording_does_not_start_when_hook_installation_fails(self):
		self.user32.hook = 0
		engine = self.module.MacroEngine()
		self.assertFalse(engine.start_recording())
		self.assertFalse(engine.is_recording)
		self.assertIsNone(engine.hook_id)

	def test_safe_recording_swallows_keys_and_retains_stop_gesture(self):
		callback_called = []
		engine = self.module.MacroEngine(safe_stop_callback=lambda: callback_called.append(True))
		self.assertTrue(engine.start_recording(safe_mode=True))

		letter = self._keyboard_data()
		result = engine.low_level_keyboard_handler(
			0,
			self.module.WM_KEYDOWN,
			ctypes.addressof(letter),
		)
		self.assertEqual(1, result)
		self.assertEqual(1, len(engine.events))

		self.user32.async_keys = {45, 16, 91}
		stop_key = self._keyboard_data(vk=self.module.VK_R)
		result = engine.low_level_keyboard_handler(
			0,
			self.module.WM_KEYDOWN,
			ctypes.addressof(stop_key),
		)
		self.assertEqual(1, result)
		self.assertEqual([True], callback_called)

	def test_live_recording_passes_events_to_windows(self):
		engine = self.module.MacroEngine()
		self.assertTrue(engine.start_recording(safe_mode=False))
		data = self._keyboard_data()
		result = engine.low_level_keyboard_handler(0, self.module.WM_KEYDOWN, ctypes.addressof(data))
		self.assertEqual(77, result)

	def test_recording_stop_gesture_and_extra_ctrl_are_not_saved(self):
		engine = self.module.MacroEngine()
		self.assertTrue(engine.start_recording(safe_mode=False))
		engine.events = [
			self._event("keyDown", vk=65, delay=0.0),
			self._event("keyUp", vk=65, delay=0.1),
			self._event("keyDown", vk=162, delay=0.05),
			self._event("keyDown", vk=45, delay=0.01),
			self._event("keyDown", vk=91, delay=0.01),
			self._event("keyDown", vk=self.module.VK_R, delay=0.01),
		]

		events, _recorded_app = engine.stop_recording()

		self.assertEqual([(65, "keyDown"), (65, "keyUp")], [(e["vkCode"], e["action"]) for e in events])
		self.assertEqual([123], self.user32.unhooked)

	def test_playback_is_single_instance_and_reports_completion(self):
		self.module.get_foreground_app = lambda: "target"
		engine = self.module.MacroEngine()
		events = [self._event("keyDown"), self._event("keyUp")]
		self.assertTrue(engine.play_macro(events, target_app="target"))
		self.assertFalse(engine.play_macro(events, target_app="target"))
		thread = engine._playback_thread
		assert thread
		thread.join(timeout=2)
		self.assertFalse(thread.is_alive())
		self.assertIn("Macro playback completed.", self.messages)
		self.assertIn("A macro is already playing.", self.messages)

	def test_application_lock_fails_closed_when_foreground_is_unknown(self):
		self.module.get_foreground_app = lambda: None
		engine = self.module.MacroEngine()
		self.assertTrue(engine.play_macro([self._event()], target_app="target"))
		thread = engine._playback_thread
		if thread:
			thread.join(timeout=3)
		self.assertEqual([], self.user32.sent)
		self.assertTrue(any("Security Warning" in message for message in self.messages))

	def test_application_lock_waits_through_transient_unknown_after_manager_closes(self):
		foreground_apps = iter([None, None, "audacity"])

		def get_foreground_app():
			return next(foreground_apps, "audacity")

		self.module.get_foreground_app = get_foreground_app
		engine = self.module.MacroEngine()
		events = [self._event("keyDown"), self._event("keyUp")]
		self.assertTrue(engine.play_macro(events, target_app="audacity"))
		thread = engine._playback_thread
		assert thread
		thread.join(timeout=2)

		self.assertFalse(thread.is_alive())
		self.assertEqual(2, len(self.user32.sent))
		self.assertIn("Macro playback completed.", self.messages)

	def test_application_lock_stops_if_foreground_changes_during_playback(self):
		foreground_apps = iter(["audacity", "audacity", "audacity", "audacity", "notepad"])
		self.module.get_foreground_app = lambda: next(foreground_apps, "notepad")
		engine = self.module.MacroEngine()
		events = [self._event("keyDown"), self._event("keyUp")]
		self.assertTrue(engine.play_macro(events, target_app="audacity"))
		thread = engine._playback_thread
		assert thread
		thread.join(timeout=2)

		self.assertFalse(thread.is_alive())
		self.assertEqual(2, len(self.user32.sent))
		self.assertFalse(self.user32.sent[0][1] & self.module.KEYEVENTF_KEYUP)
		self.assertTrue(self.user32.sent[1][1] & self.module.KEYEVENTF_KEYUP)
		self.assertTrue(any("active application changed" in message for message in self.messages))

	def test_active_application_uses_nvda_focus_object_when_win32_reports_nvda(self):
		self.module.get_foreground_app = lambda: "nvda"
		focus_object = types.SimpleNamespace(appModule=types.SimpleNamespace(appName="notepad"))
		self.stubs["api"].getFocusObject = lambda: focus_object
		self.stubs["api"].getForegroundObject = lambda: None

		self.assertEqual("notepad", self.module.get_active_application())

	def test_global_plugin_remembers_last_non_nvda_focus_application(self):
		plugin = self.module.GlobalPlugin()
		next_calls = []

		plugin.event_gainFocus(
			types.SimpleNamespace(appModule=types.SimpleNamespace(appName="winword")),
			lambda: next_calls.append(True),
		)
		self.assertEqual("winword", plugin.last_external_app)
		plugin.event_gainFocus(
			types.SimpleNamespace(appModule=types.SimpleNamespace(appName="nvda")),
			lambda: next_calls.append(True),
		)

		self.assertEqual("winword", plugin.last_external_app)
		self.assertEqual([True, True], next_calls)
		plugin.terminate()

	def test_editor_application_lock_persists_and_blocks_another_application(self):
		storage = self.module.MacroStorage()
		macro = storage.save_macro("Locked", 1, 1.0, None, "winword", [self._event()])
		preferred_app = self.module.get_preferred_lock_app(macro)
		self.assertEqual("winword", preferred_app)
		target_app = self.module.resolve_target_application(True, preferred_app)
		self.assertTrue(storage.update_macro(0, {"target_app": target_app}))

		reloaded = self.module.MacroStorage()
		self.assertEqual("winword", reloaded.macros[0]["target_app"])
		self.assertEqual(
			"legacyTarget",
			self.module.get_preferred_lock_app({"target_app": "legacyTarget", "recorded_app": None}),
		)

		self.module.get_foreground_app = lambda: "notepad"
		engine = self.module.MacroEngine()
		self.assertTrue(engine.play_macro(reloaded.macros[0]["events"], target_app="winword"))
		thread = engine._playback_thread
		if thread:
			thread.join(timeout=1)
		self.assertEqual([], self.user32.sent)

	def test_editor_application_lock_uses_app_active_before_manager_opened(self):
		storage = self.module.MacroStorage()
		macro = storage.save_macro("Legacy", 1, 1.0, None, None, [self._event()])

		preferred_app = self.module.get_preferred_lock_app(macro, "winword")
		self.assertEqual("winword", preferred_app)
		target_app = self.module.resolve_target_application(True, preferred_app)
		self.assertTrue(storage.update_macro(0, {"target_app": target_app}))

		reloaded = self.module.MacroStorage()
		self.assertEqual("winword", reloaded.macros[0]["target_app"])
		self.assertEqual("winword", self.module.get_preferred_lock_app(reloaded.macros[0], "notepad"))

	def test_application_lock_is_not_silently_saved_for_nvda(self):
		self.module.get_foreground_app = lambda: "nvda"
		with self.assertRaises(self.module.MacroValidationError):
			self.module.resolve_target_application(True)
		with self.assertRaises(self.module.MacroValidationError):
			self.module.resolve_target_application(True, "nvda")

	def test_playback_failure_releases_only_injected_pressed_keys(self):
		self.module.get_foreground_app = lambda: "target"
		self.user32.fail_send_number = 2
		engine = self.module.MacroEngine()
		self.assertTrue(engine.play_macro([self._event("keyDown"), self._event("keyUp")]))
		thread = engine._playback_thread
		assert thread
		thread.join(timeout=2)
		self.assertGreaterEqual(len(self.user32.sent), 2)
		self.assertTrue(self.user32.sent[-1][1] & self.module.KEYEVENTF_KEYUP)
		self.assertIn("Macro playback failed. See the NVDA log for details.", self.messages)

	def test_cancel_does_not_release_physical_modifier_from_stop_gesture(self):
		self.module.get_foreground_app = lambda: "target"
		self.user32.async_keys = {17, 162}
		engine = self.module.MacroEngine()
		first_event_sent = threading.Event()
		original_send = engine._send_key_event

		def send_and_signal(event, **kwargs):
			original_send(event, **kwargs)
			if event["action"] == "keyDown":
				first_event_sent.set()

		engine._send_key_event = send_and_signal
		events = [self._event("keyDown"), self._event("keyUp", delay=10.0)]
		self.assertTrue(engine.play_macro(events))
		self.assertTrue(first_event_sent.wait(timeout=1.0))
		engine.stop_playback_event.set()
		thread = engine._playback_thread
		assert thread
		thread.join(timeout=2)

		self.assertFalse(thread.is_alive())
		self.assertEqual([65, 65], [vk for vk, _flags in self.user32.sent])
		self.assertFalse(self.user32.sent[0][1] & self.module.KEYEVENTF_KEYUP)
		self.assertTrue(self.user32.sent[1][1] & self.module.KEYEVENTF_KEYUP)
		self.assertIn("Macro playback canceled.", self.messages)

	def test_start_delay_is_independent_of_playback_speed(self):
		self.module.get_foreground_app = lambda: "target"
		engine = self.module.MacroEngine()
		waits = []
		start_wait_seen = threading.Event()
		release_start_wait = threading.Event()

		def record_wait(timeout):
			waits.append(timeout)
			if timeout == 0.75:
				start_wait_seen.set()
				release_start_wait.wait(timeout=1.0)
			return False

		with mock.patch.object(engine.stop_playback_event, "wait", side_effect=record_wait):
			self.assertTrue(
				engine.play_macro(
					[self._event("keyDown", delay=1.0), self._event("keyUp", delay=1.0)],
					speed=4.0,
					start_delay=0.75,
				),
			)
			self.assertTrue(start_wait_seen.wait(timeout=1.0))
			thread = engine._playback_thread
			assert thread
			release_start_wait.set()
			thread.join(timeout=2)

		self.assertFalse(thread.is_alive())
		self.assertEqual(0.75, waits[0])
		self.assertEqual(2, waits.count(0.25))

	def test_start_delay_can_be_canceled_before_any_key_is_sent(self):
		self.module.get_foreground_app = lambda: "target"
		engine = self.module.MacroEngine()
		start_wait_seen = threading.Event()
		release_start_wait = threading.Event()

		def cancel_during_wait(timeout):
			if timeout == 2.5:
				start_wait_seen.set()
				release_start_wait.wait(timeout=1.0)
				engine.stop_playback_event.set()
				return True
			return False

		with mock.patch.object(engine.stop_playback_event, "wait", side_effect=cancel_during_wait):
			self.assertTrue(engine.play_macro([self._event()], start_delay=2.5))
			self.assertTrue(start_wait_seen.wait(timeout=1.0))
			thread = engine._playback_thread
			assert thread
			release_start_wait.set()
			thread.join(timeout=2)

		self.assertFalse(thread.is_alive())
		self.assertEqual([], self.user32.sent)
		self.assertIn("Macro playback canceled.", self.messages)

	def test_storage_validates_import_and_repairs_missing_id_on_load(self):
		path = Path(self.temp_dir.name) / "nvda_macros.json"
		path.write_text(
			json.dumps(
				[
					{
						"name": "Legacy",
						"events": [self._event()],
					},
				],
			),
			encoding="utf-8",
		)
		storage = self.module.MacroStorage()
		self.assertRegex(storage.macros[0]["id"], r"^[0-9a-f]{32}$")
		self.assertEqual(0.0, storage.macros[0]["start_delay"])
		persisted = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual(storage.macros[0]["id"], persisted[0]["id"])
		with self.assertRaises(self.module.MacroValidationError):
			storage.import_macro({"name": "Bad", "events": [{"action": "launchProgram"}]})
		with self.assertRaises(self.module.MacroValidationError):
			storage.save_macro(
				"Bad delay",
				1,
				1.0,
				None,
				None,
				[self._event()],
				self.module.MAX_START_DELAY_SECONDS + 1,
			)

	def test_storage_write_is_atomic_and_rolls_back_failed_update(self):
		storage = self.module.MacroStorage()
		storage.save_macro("One", 1, 1.0, None, None, [self._event()])
		storage.save_macro("Two", 1, 1.0, None, None, [self._event(vk=66)])
		self.assertTrue(Path(storage.backup_path).exists())
		original = storage.macros[0]["name"]
		with mock.patch.object(storage, "_write_to_file", side_effect=self.module.MacroStorageError("disk")):
			with self.assertRaises(self.module.MacroStorageError):
				storage.update_macro(0, {"name": "Changed"})
		self.assertEqual(original, storage.macros[0]["name"])

	def test_clipboard_import_rejects_excessive_decompressed_payload(self):
		payload = b"x" * (self.module.MAX_DECOMPRESSED_MACRO_BYTES + 1)
		encoded = base64.b64encode(zlib.compress(payload)).decode("ascii")
		self.stubs["api"].getClipData = lambda: f"NVDAMacro::{encoded}"
		storage = self.module.MacroStorage()
		success, _message = storage.import_macro_from_clipboard()
		self.assertFalse(success)

	def test_shared_macro_uses_edited_loop_count_from_cached_dynamic_script(self):
		clipboard = []
		self.stubs["api"].copyToClip = lambda text: not clipboard.append(text)
		self.stubs["api"].getClipData = lambda: clipboard[-1]

		sender_path = Path(self.temp_dir.name) / "sender"
		self.stubs["globalVars"].appArgs.configPath = str(sender_path)
		sender = self.module.MacroStorage()
		sender.save_macro(
			"Shared",
			1,
			1.0,
			None,
			None,
			[self._event("keyDown"), self._event("keyUp")],
			0.75,
		)
		self.assertTrue(sender.export_macro_to_clipboard(0))

		receiver_path = Path(self.temp_dir.name) / "receiver"
		self.stubs["globalVars"].appArgs.configPath = str(receiver_path)
		receiver = self.module.MacroStorage()
		success, _name = receiver.import_macro_from_clipboard()
		self.assertTrue(success)
		self.assertEqual(1, receiver.macros[0]["loop_count"])
		self.assertEqual(0.75, receiver.macros[0]["start_delay"])

		plugin = self.module.GlobalPlugin()
		macro_id = plugin.storage.macros[0]["id"]
		func_name = f"script_dynmacro_{macro_id}"
		cached_script = getattr(type(plugin), func_name)
		self.assertTrue(plugin.storage.update_macro(0, {"loop_count": 4, "start_delay": 1.25}))

		plugin.engine.play_macro = mock.Mock(return_value=True)
		cached_script(plugin, None)
		self.assertEqual(4, plugin.engine.play_macro.call_args.args[1])
		self.assertEqual(1.25, plugin.engine.play_macro.call_args.args[4])
		self.assertEqual(4, self.module.MacroStorage().macros[0]["loop_count"])

		self.module.get_foreground_app = lambda: "notepad"
		engine = self.module.MacroEngine()
		self.assertTrue(
			engine.play_macro(
				plugin.storage.macros[0]["events"],
				plugin.storage.macros[0]["loop_count"],
			),
		)
		thread = engine._playback_thread
		assert thread
		thread.join(timeout=2)
		self.assertFalse(thread.is_alive())
		self.assertEqual(8, len(self.user32.sent))
		plugin.terminate()

	def test_editor_round_trip_preserves_key_hold_delay(self):
		dialog = object()
		raw = [self._event("keyDown", delay=0.25), self._event("keyUp", delay=0.42)]
		linear = self.module.MacroEditDialog._linearize_events(dialog, raw)
		self.assertEqual(0.42, linear[1]["hold"])
		rebuilt = self.module.MacroEditDialog._rebuild_events(dialog, linear)
		self.assertEqual(0.25, rebuilt[0]["delay"])
		self.assertEqual(0.42, rebuilt[1]["delay"])

	def test_start_delay_parser_accepts_decimal_comma_and_blank_input(self):
		combo = types.SimpleNamespace(GetValue=lambda: "0,75")
		dialog = types.SimpleNamespace(start_delay_combo=combo)
		self.assertEqual(0.75, self.module.MacroEditDialog._parse_start_delay(dialog))

		combo.GetValue = lambda: ""
		self.assertEqual(0.0, self.module.MacroEditDialog._parse_start_delay(dialog))

	def test_translation_catalogs_match_source_and_preserve_placeholders(self):
		messages = {}
		for source in update_translations.SOURCE_FILES:
			messages.update(update_translations.extract_messages(source))
		expected = set(messages)
		placeholder_pattern = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
		catalog_paths = list(update_translations.LOCALE_ROOT.glob("*/LC_MESSAGES/nvda.po"))
		self.assertEqual({"de", "es", "pt_PT", "tr"}, {path.parts[-3] for path in catalog_paths})
		for po_path in catalog_paths:
			catalog = polib.pofile(str(po_path))
			self.assertEqual(expected, {entry.msgid for entry in catalog})
			self.assertFalse(catalog.untranslated_entries(), po_path.parts[-3])
			for entry in catalog.translated_entries():
				source_fields = sorted(placeholder_pattern.findall(entry.msgid))
				translated_fields = sorted(placeholder_pattern.findall(entry.msgstr))
				self.assertEqual(source_fields, translated_fields, entry.msgid)
			doc_path = ROOT / "addon/doc" / po_path.parts[-3] / "readme.md"
			self.assertTrue(doc_path.exists(), doc_path)


if __name__ == "__main__":
	unittest.main()
