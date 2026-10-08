"""Additional regressions migrated to the verified upstream 1.2.8 code base."""

import ctypes
import itertools
import types
import unittest
from unittest.mock import Mock, patch

from test_nvda_macro_manager import _load_addon, ROOT

plugin, _modules, _messages = _load_addon(str(ROOT))


class WinFunction:
	def __init__(self, result=0):
		self.result = result

	def __call__(self, *args):
		return self.result


class FakeUser32:
	def __init__(self):
		self.SetWindowsHookExW = WinFunction(123)
		self.CallNextHookEx = WinFunction()
		self.UnhookWindowsHookEx = WinFunction(1)
		self.SendInput = WinFunction(1)
		self.SendMessageW = WinFunction()
		self.GetAsyncKeyState = WinFunction()
		self.MapVirtualKeyW = WinFunction(30)


def key(action, vk=65, delay=0, scan=None, extended=False):
	if scan is None:
		scan = {32: 57, 65: 30, 66: 48, 160: 42, 161: 54, 162: 29, 163: 29}.get(vk, 30)
	return dict(action=action, vkCode=vk, scanCode=scan, extended=extended, delay=delay)


class RecordingTests(unittest.TestCase):
	def setUp(self):
		self.engine = plugin.MacroEngine(recording_command_callback=Mock())
		self.io = FakeUser32()
		self.patches = [
			patch.object(plugin, "user32", self.io),
			patch.object(plugin, "get_foreground_app", return_value="notepad"),
		]
		for item in self.patches:
			item.start()
			self.addCleanup(item.stop)

	def emit(self, vk, down, scan=30, extended=False, injected=False):
		data = plugin.KBDLLHOOKSTRUCT(
			vkCode=vk, scanCode=scan, flags=(1 if extended else 0) | (16 if injected else 0)
		)
		return self.engine.low_level_keyboard_handler(
			0, plugin.WM_KEYDOWN if down else plugin.WM_KEYUP, ctypes.pointer(data)
		)

	def test_ctrl_space_modifier_repeat_is_filtered(self):
		self.engine.start_recording()
		for vk, down in [(162, True), (162, True), (162, True), (32, True), (32, False), (162, False)]:
			self.emit(vk, down)
		events, app = self.engine.stop_recording()
		self.assertEqual(
			[(e["action"], e["vkCode"]) for e in events],
			[("keyDown", 162), ("keyDown", 32), ("keyUp", 32), ("keyUp", 162)],
		)
		self.assertEqual(app, "notepad")

	def test_letter_and_space_autorepeat_are_preserved(self):
		self.engine.start_recording()
		for vk in (65, 32):
			self.emit(vk, True)
			self.emit(vk, True)
			self.emit(vk, False)
		events, _app = self.engine.stop_recording()
		self.assertEqual(len(events), 6)

	def test_stop_does_not_delete_recent_real_events(self):
		self.engine.start_recording()
		self.emit(65, True)
		self.emit(65, False)
		self.assertEqual(len(self.engine.stop_recording()[0]), 2)

	def test_control_chord_removed_without_losing_previous_key(self):
		self.engine.start_recording()
		self.emit(65, True)
		self.emit(65, False)
		self.emit(45, True, extended=True)
		self.emit(91, True, extended=True)
		self.emit(82, True)
		events, _app = self.engine.stop_recording()
		self.assertEqual([e["vkCode"] for e in events], [65, 65])

	def test_safe_mode_blocks_all_ctrl_shift_delete_events(self):
		self.engine.start_recording(safe_mode=True)
		for vk, down in [(162, True), (160, True), (46, True), (46, False), (160, False), (162, False)]:
			self.assertEqual(self.emit(vk, down), 1)

	def test_safe_mode_stop_chord_is_dispatched_without_leaking_keys(self):
		self.engine.start_recording(safe_mode=True)
		self.assertEqual(self.emit(45, True, extended=True), 1)
		self.assertEqual(self.emit(91, True, extended=True), 1)
		self.assertEqual(self.emit(160, True), 1)
		self.assertEqual(self.emit(82, True), 1)
		self.engine._recording_command_callback.assert_called_once_with("stop")
		self.assertEqual(self.engine.stop_recording()[0], [])

	def test_initial_shortcut_key_ups_are_not_recorded(self):
		self.io.GetAsyncKeyState = lambda vk: 0x8000 if vk in (45, 91, 82) else 0
		self.engine.start_recording()
		self.emit(82, False)
		self.emit(91, False, extended=True)
		self.emit(45, False, extended=True)
		self.emit(65, True)
		self.emit(65, False)
		self.assertEqual([e["vkCode"] for e in self.engine.stop_recording()[0]], [65, 65])
		self.assertFalse(self.engine._physical_keys)

	def test_hook_failure_does_not_claim_recording_started(self):
		self.io.SetWindowsHookExW.result = 0
		self.assertFalse(self.engine.start_recording())
		self.assertFalse(self.engine.is_recording)

	def test_injected_events_are_ignored(self):
		self.engine.start_recording(safe_mode=True)
		self.assertEqual(self.emit(65, True, injected=True), 0)
		self.assertEqual(self.engine.events, [])

	def test_initial_held_letter_repeat_is_not_recorded(self):
		self.io.GetAsyncKeyState = lambda vk: 0x8000 if vk == 82 else 0
		self.engine.start_recording()
		self.emit(82, True)
		self.emit(82, False)
		self.emit(65, True)
		self.emit(65, False)
		self.assertEqual([e["vkCode"] for e in self.engine.stop_recording()[0]], [65, 65])

	def test_stop_while_key_held_preserves_hold_duration(self):
		with patch.object(plugin.time, "perf_counter", side_effect=[10.0, 10.1, 12.1]):
			self.engine.start_recording()
			self.emit(65, True)
			events, _app = self.engine.stop_recording()
		self.assertEqual(events[-1]["action"], "keyUp")
		self.assertAlmostEqual(events[-1]["delay"], 2.0)

	def test_repeat_of_blocked_shift_stays_blocked_after_nvda_down(self):
		self.engine.start_recording(safe_mode=True)
		self.assertEqual(self.emit(160, True), 1)
		self.emit(45, True, extended=True)
		self.assertEqual(self.emit(160, True), 1)
		self.assertEqual(self.emit(160, False), 1)

	def test_ordinary_typing_never_escapes_safe_mode_control_prefix(self):
		self.engine.start_recording(safe_mode=True)
		self.emit(45, True, extended=True)
		for vk in (160, 91, 65, 32):
			self.assertEqual(self.emit(vk, True), 1)
			self.assertEqual(self.emit(vk, False), 1)

	def test_safe_stop_all_modifier_orders_and_nvda_key_choices(self):
		for mask, nvda, extended in ((1, 20, False), (2, 45, False), (4, 45, True)):
			for order in itertools.permutations((nvda, 91, 160)):
				with (
					self.subTest(mask=mask, order=order),
					patch.dict(plugin.config.conf["keyboard"], NVDAModifierKeys=mask),
				):
					self.engine = plugin.MacroEngine(recording_command_callback=Mock())
					self.engine.start_recording(safe_mode=True)
					for vk in order:
						self.assertEqual(
							self.emit(vk, True, extended=extended if vk == nvda else vk == 91), 1
						)
					self.assertEqual(self.emit(82, True), 1)
					self.emit(82, True)
					self.engine._recording_command_callback.assert_called_once_with("stop")
					self.assertEqual(self.engine.stop_recording()[0], [])

	def test_ctrl_space_both_release_orders(self):
		for releases in ((162, 32), (32, 162)):
			with self.subTest(releases=releases):
				self.engine.start_recording()
				self.emit(162, True, scan=29)
				self.emit(32, True, scan=57)
				for vk in releases:
					self.emit(vk, False, scan=29 if vk == 162 else 57)
				events, _app = self.engine.stop_recording()
				self.assertEqual(
					[(e["action"], e["vkCode"]) for e in events],
					[("keyDown", 162), ("keyDown", 32)] + [("keyUp", vk) for vk in releases],
				)

	def test_safe_initial_key_release_reaches_original_listener(self):
		self.io.GetAsyncKeyState = lambda vk: 0x8000 if vk == 82 else 0
		self.engine.start_recording(safe_mode=True)
		self.assertEqual(self.emit(82, True), 1)
		self.assertEqual(self.emit(82, False), 0)
		self.assertEqual(self.engine.stop_recording()[0], [])

	def test_both_insert_keys_are_tracked_independently_after_start(self):
		self.engine.start_recording()
		self.emit(45, True, extended=True)
		self.emit(45, True, extended=False)
		self.emit(45, False, extended=False)
		self.assertIn((45, True), self.engine._physical_keys)
		self.assertNotIn((45, False), self.engine._physical_keys)
		self.emit(45, False, extended=True)
		self.engine.stop_recording()

	def test_custom_safe_control_chord_dispatches_and_trims_only_chord(self):
		self.engine._command_resolver = (
			lambda vk, scan, extended, held: "stop"
			if vk == 120 and (162, False) in held and (164, False) in held
			else None
		)
		self.engine.start_recording(safe_mode=True)
		self.emit(65, True)
		self.emit(65, False)
		for vk in (162, 164, 120):
			self.assertEqual(self.emit(vk, True), 1)
		self.engine._recording_command_callback.assert_called_once_with("stop")
		self.assertEqual([e["vkCode"] for e in self.engine.stop_recording()[0]], [65, 65])

	def test_pending_safe_stop_does_not_record_queued_keys(self):
		queue = []
		with patch.object(plugin.core, "callLater", side_effect=lambda delay, *args: queue.append(args)):
			self.engine.start_recording(safe_mode=True)
			self.emit(45, True, extended=True)
			self.emit(91, True, extended=True)
			self.emit(82, True)
			for vk, down in ((66, True), (66, False), (82, True)):
				self.assertEqual(self.emit(vk, down), 1)
		self.assertEqual(len(queue), 1)
		self.assertEqual(self.engine.stop_recording()[0], [])

	def test_nvda_swallowed_initial_shortcut_does_not_stop_on_repeat(self):
		self.engine.start_recording(safe_mode=True, initial_keys={(45, True), (91, True), (82, False)})
		self.emit(82, True)
		self.emit(82, False)
		self.emit(91, False, extended=True)
		self.emit(45, False, extended=True)
		self.engine._recording_command_callback.assert_not_called()
		self.emit(65, True)
		self.emit(65, False)
		self.assertEqual([e["vkCode"] for e in self.engine.stop_recording()[0]], [65, 65])

	def test_nvda_modifier_snapshot_preserves_exact_insert_location(self):
		with patch.object(plugin.keyboardHandler, "currentModifiers", {(45, True)}, create=True):
			self.io.GetAsyncKeyState = lambda vk: 0x8000 if vk == 45 else 0
			self.engine.start_recording(safe_mode=True)
			self.assertEqual(self.engine._initial_keys, {(45, True)})
			self.emit(45, True, extended=False)
			self.emit(45, False, extended=False)
			self.assertIn((45, True), self.engine._physical_keys)
			events, _app = self.engine.stop_recording()
			self.assertEqual([e["extended"] for e in events], [False, False])


class EditorTests(unittest.TestCase):
	def setUp(self):
		self.editor = plugin.MacroEditDialog.__new__(plugin.MacroEditDialog)

	def test_long_hold_has_explicit_down_wait_up_and_roundtrips(self):
		events = [key("keyDown", delay=0.2), key("keyUp", delay=2)]
		linear = self.editor._linearize_events(events)
		self.assertEqual([e["type"] for e in linear], ["delay", "keyDown", "delay", "keyUp"])
		self.assertEqual(self.editor._rebuild_events(linear), events)

	def test_short_press_is_one_step_and_preserves_recorded_duration(self):
		events = [key("keyDown"), key("keyUp", delay=0.08)]
		linear = self.editor._linearize_events(events)
		self.assertEqual([e["type"] for e in linear], ["press"])
		self.assertEqual(self.editor._rebuild_events(linear), events)

	def test_new_press_uses_standard_duration(self):
		events = self.editor._rebuild_events([dict(type="press", vkCode=32, scanCode=57, extended=False)])
		self.assertEqual(events[1]["delay"], plugin.STANDARD_PRESS_TIME)

	def test_ctrl_stays_as_separate_down_and_up(self):
		events = [key("keyDown", 162), key("keyDown", 32), key("keyUp", 32, delay=0.08), key("keyUp", 162)]
		linear = self.editor._linearize_events(events)
		self.assertEqual([e["type"] for e in linear], ["keyDown", "press", "keyUp"])
		self.assertEqual(self.editor._rebuild_events(linear), events)

	def test_trailing_and_standalone_wait_survive_save(self):
		for events in [
			[dict(action="delay", delay=2)],
			[key("keyDown"), key("keyUp"), dict(action="delay", delay=2)],
		]:
			self.assertEqual(self.editor._rebuild_events(self.editor._linearize_events(events)), events)

	def test_generated_overlapping_timelines_preserve_behavior(self):
		import random

		generator = random.Random(22023)

		def timeline(events):
			elapsed, steps = 0.0, []
			for event in events:
				elapsed += event["delay"]
				if event["action"] != "delay":
					steps.append(
						(
							event["action"],
							event["vkCode"],
							event["scanCode"],
							event.get("extended", False),
							elapsed,
						)
					)
			return steps, elapsed

		for scenario in range(1000):
			events = []
			held = set()
			for _step in range(generator.randint(1, 50)):
				vk = generator.choice((32, 65, 66, 160, 162, 163))
				action = generator.choice(("keyDown", "keyUp", "delay"))
				delay = generator.choice((0, 0.001, 0.035, 0.08, 0.2, 0.21, 1.7))
				if action == "delay":
					events.append(dict(action=action, delay=delay))
				elif action == "keyDown":
					events.append(key(action, vk, delay, scan=vk, extended=vk == 163))
					held.add(vk)
				elif vk in held:
					events.append(key(action, vk, delay, scan=vk, extended=vk == 163))
					held.remove(vk)
			for vk in held:
				events.append(key("keyUp", vk, 0.05, scan=vk, extended=vk == 163))
			before, end_before = timeline(events)
			after, end_after = timeline(self.editor._rebuild_events(self.editor._linearize_events(events)))
			with self.subTest(scenario=scenario):
				self.assertEqual([e[:4] for e in before], [e[:4] for e in after])
				for original, rebuilt in zip(before, after):
					self.assertAlmostEqual(original[-1], rebuilt[-1], places=8)
				self.assertAlmostEqual(end_before, end_after, places=8)

	def test_milliseconds_reject_non_decimal_unicode_and_huge_input(self):
		for value in ("", "²", "½", "-1", "NaN", "1.5", "9" * 5000):
			with self.subTest(length=len(value)), self.assertRaises(ValueError):
				plugin.parse_milliseconds(value)
		self.assertEqual(plugin.parse_milliseconds("1000"), 1.0)
		self.assertEqual(plugin.parse_milliseconds("０"), 0.0)


class CommandIntegrationTests(unittest.TestCase):
	def setUp(self):
		self.instance = plugin.GlobalPlugin.__new__(plugin.GlobalPlugin)
		self.instance.engine = plugin.MacroEngine()
		self.instance._recording_commands = {}
		self.instance._recording_command_keys = set()

		def normalize(value):
			prefix, chord = value.lower().split(":", 1)
			return prefix + ":" + "+".join(sorted(chord.split("+")))

		class Gesture:
			def __init__(self, modifiers, vk, scan, extended):
				self.vkCode = vk
				names = [
					{162: "control", 164: "alt", 160: "shift", 45: "nvda", 91: "windows"}[key[0]]
					for key in modifiers
				]
				main = {120: "f9", 82: "r", 77: "m"}[vk]
				self.identifiers = [
					"kb:" + "+".join(names + [main]),
					"kb(desktop):" + "+".join(names + [main]),
				]

			@classmethod
			def fromName(cls, name):
				return types.SimpleNamespace(
					vkCode=120 if "f9" in name else 82 if "r" in name.split("+") else 77
				)

		self.patches = [
			patch.object(plugin.inputCore, "normalizeGestureIdentifier", side_effect=normalize, create=True),
			patch.object(plugin.keyboardHandler, "KeyboardInputGesture", Gesture, create=True),
			patch.dict(plugin.config.conf["keyboard"], keyboardLayout="desktop"),
		]
		for item in self.patches:
			item.start()
			self.addCleanup(item.stop)

	def load_mappings(self, infos):
		mappings = {"Macro Manager": {str(index): info for index, info in enumerate(infos)}}
		with patch.object(
			plugin.inputCore,
			"manager",
			types.SimpleNamespace(getAllGestureMappings=lambda: mappings),
			create=True,
		):
			self.instance._refresh_recording_commands()

	def info(self, script="toggleMacroRecordingSafe", gesture="kb:control+alt+f9", cls=None):
		return types.SimpleNamespace(cls=cls or plugin.GlobalPlugin, scriptName=script, gestures=[gesture])

	def test_remapped_recording_chord_resolves_in_either_modifier_order(self):
		self.load_mappings([self.info()])
		self.assertEqual(
			self.instance._resolve_recording_command(
				120, 67, False, {(120, False), (162, False), (164, False)}
			),
			"stop",
		)
		self.assertIsNone(
			self.instance._resolve_recording_command(
				120, 67, False, {(120, False), (162, False), (164, False), (160, False)}
			)
		)

	def test_other_layout_and_other_plugins_are_not_recorder_commands(self):
		self.load_mappings([self.info(gesture="kb(laptop):control+alt+f9"), self.info(cls=object)])
		self.assertEqual(self.instance._recording_commands, {})

	def test_open_manager_and_unbound_recording_commands(self):
		self.load_mappings([self.info(script="openMacroInterface", gesture="kb:nvda+shift+m")])
		self.assertEqual(
			self.instance._resolve_recording_command(77, 50, False, {(77, False), (45, True), (160, False)}),
			"open",
		)
		self.assertIsNone(
			self.instance._resolve_recording_command(82, 19, False, {(82, False), (45, True), (91, True)})
		)

	def test_mapping_api_failure_preserves_default_stop_fallback(self):
		with patch.object(
			plugin.inputCore,
			"manager",
			types.SimpleNamespace(getAllGestureMappings=Mock(side_effect=RuntimeError())),
			create=True,
		):
			self.instance._refresh_recording_commands()
		self.assertIsNone(self.instance.engine._command_resolver)

	def test_dynamic_scripts_capture_their_own_macro_and_preserve_legacy_id(self):
		self.instance.engine = Mock(is_recording=False, is_playing=False)
		macros = [
			dict(id="10.25", name="First", events=[key("keyDown")]),
			dict(id="10_25", name="Second", events=[key("keyDown", 66)]),
		]
		self.instance.storage = types.SimpleNamespace(macros=macros)
		self.instance.inject_dynamic_scripts()
		try:
			for macro in macros:
				script = getattr(self.instance, "script_dynmacro_" + plugin.macro_script_id(macro["id"]))
				script(None)
			self.assertEqual(
				[call.args[0] for call in self.instance.engine.play_macro.call_args_list],
				[macro["events"] for macro in macros],
			)
		finally:
			self.instance.storage.macros = []
			self.instance.inject_dynamic_scripts()

	def test_temporary_shortcut_reports_worker_start_failure(self):
		self.instance.last_recorded_events = [key("keyDown")]
		with (
			patch.object(self.instance.engine, "play_macro", side_effect=RuntimeError("thread unavailable")),
			patch.object(plugin.ui, "message") as message,
		):
			self.instance.script_playLastMacro(None)
		message.assert_called_once_with("Macro playback failed. See the NVDA log for details.")

	def test_dynamic_shortcut_reports_invalid_scaled_timing(self):
		macro = dict(id="test", name="Very slow", events=[key("keyDown", delay=1)], speed=1e-320)
		self.instance.storage = types.SimpleNamespace(macros=[macro])
		self.instance.inject_dynamic_scripts()
		try:
			with patch.object(plugin.ui, "message") as message:
				self.instance.script_dynmacro_test(None)
			message.assert_called_once_with("Cannot play this macro because its data is invalid.")
			self.assertFalse(self.instance.engine.is_playing)
		finally:
			self.instance.storage.macros = []
			self.instance.inject_dynamic_scripts()


class InterfaceTests(unittest.TestCase):
	def setUp(self):
		self.editor = plugin.MacroEditDialog.__new__(plugin.MacroEditDialog)
		self.editor.events_list = Mock()
		self.action = Mock()
		self.editor._list_shortcuts = {(127, False): self.action, (ord("C"), True): self.action}
		self.focus = self.editor.events_list
		self.constants = patch.multiple(
			plugin.wx,
			create=True,
			WXK_ESCAPE=27,
			WXK_SPACE=32,
			WXK_DELETE=127,
			Window=types.SimpleNamespace(FindFocus=lambda: self.focus),
		)
		self.constants.start()
		self.addCleanup(self.constants.stop)

	def event(self, code, ctrl=False):
		return Mock(
			GetKeyCode=lambda: code, ControlDown=lambda: ctrl, AltDown=lambda: False, ShiftDown=lambda: False
		)

	def test_text_field_copy_is_not_macro_copy(self):
		self.focus = Mock()
		event = self.event(ord("C"), ctrl=True)
		self.editor.on_escape_press(event)
		self.action.assert_not_called()
		event.Skip.assert_called_once()

	def test_text_field_ctrl_space_is_not_swallowed(self):
		self.focus = Mock()
		event = self.event(32, ctrl=True)
		self.editor.on_escape_press(event)
		event.Skip.assert_called_once()

	def test_delete_shortcut_only_acts_inside_events_list(self):
		event = self.event(127)
		self.editor.on_escape_press(event)
		self.action.assert_called_once_with(None)
		event.Skip.assert_not_called()

	def test_ctrl_space_uses_caret_on_multiple_selection_list(self):
		self.editor.events_list.GetHandle.return_value = 987
		self.editor.events_list.GetCount.return_value = 4
		self.editor.events_list.IsSelected.return_value = False
		self.editor.on_list_select = Mock()
		with patch.object(plugin.user32, "SendMessageW", return_value=2) as send:
			self.editor.on_escape_press(self.event(32, ctrl=True))
		send.assert_called_once_with(987, 0x019F, 0, 0)
		self.editor.events_list.Select.assert_called_once_with(2)
		self.editor.events_list.GetSelection.assert_not_called()
