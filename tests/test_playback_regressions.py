"""Playback and persistence scenarios against the upstream-based implementation."""

import threading
import types
import unittest
from unittest import mock

import test_nvda_macro_manager as baseline


class PlaybackRegressions(unittest.TestCase):
	setUp = baseline.MacroManagerTests.setUp
	_event = baseline.MacroManagerTests._event

	def play(self, events, **kwargs):
		engine = self.module.MacroEngine()
		self.assertTrue(engine.play_macro(events, **kwargs))
		thread = engine._playback_thread
		if thread:
			thread.join(timeout=2)
			self.assertFalse(thread.is_alive())
		self.assertFalse(engine.is_playing)
		return engine

	def test_invalid_actions_and_overflow_are_validation_errors(self):
		for event in ({"action": []}, self._event(delay=10**1000), dict(self._event(), extended="yes")):
			with (
				self.subTest(event_type=type(event.get("action"))),
				self.assertRaises(self.module.MacroValidationError),
			):
				self.module.MacroStorage._normalize_event(event)

	def test_worker_construction_failure_restores_idle(self):
		engine = self.module.MacroEngine()
		with mock.patch.object(self.module.threading, "Thread", side_effect=RuntimeError("unavailable")):
			self.assertFalse(engine.play_macro([self._event()]))
		self.assertFalse(engine.is_playing)
		engine.shutdown()

	def test_worker_start_failure_can_be_retried(self):
		engine = self.module.MacroEngine()
		with mock.patch.object(
			self.module.threading.Thread, "start", side_effect=RuntimeError("unavailable")
		):
			self.assertFalse(engine.play_macro([self._event()]))
		engine.shutdown()
		self.assertTrue(engine.play_macro([self._event(), self._event("keyUp", delay=0.1)]))
		engine.shutdown()
		self.assertFalse(engine.is_playing)

	def test_overflowed_scaled_delay_is_rejected(self):
		engine = self.module.MacroEngine()
		self.assertFalse(engine.play_macro([self._event(delay=1)], speed=1e-320))
		self.assertFalse(engine.is_playing)
		self.assertEqual([], self.user32.sent)

	def test_unmatched_key_up_is_not_sent(self):
		self.play([self._event("keyUp")])
		self.assertEqual([], self.user32.sent)

	def test_virtual_and_scan_code_identity_match(self):
		self.play([self._event(), dict(self._event("keyUp"), scanCode=0)])
		self.assertEqual(2, len(self.user32.sent))
		self.assertTrue(self.user32.sent[-1][1] & self.module.KEYEVENTF_KEYUP)

	def test_extended_scan_code_input_flags(self):
		event = dict(self._event(vk=163), scanCode=29, extended=True)
		self.play([event, dict(event, action="keyUp")])
		self.assertEqual([(0, 29, 9), (0, 29, 11)], self.user32.raw_sent)

	def test_pause_uses_virtual_code_for_its_e1_sequence(self):
		down = dict(self._event(vk=19), scanCode=69)
		self.play([down, dict(down, action="keyUp", scanCode=0)])
		self.assertEqual([19, 19], [vk for vk, _scan, _flags in self.user32.raw_sent])
		self.assertEqual([0, 2], [flags for _vk, _scan, flags in self.user32.raw_sent])

	def test_temporary_cleanup_failure_is_retried(self):
		self.user32.fail_send_number = 2
		self.play([self._event()])
		self.assertEqual(3, self.user32.send_calls)
		self.assertTrue(self.user32.sent[-1][1] & self.module.KEYEVENTF_KEYUP)
		self.assertIn("Macro playback failed. See the NVDA log for details.", self.messages)

	def test_persistent_cleanup_failure_is_not_announced_as_completion(self):
		engine = self.module.MacroEngine()

		def send(event, *, force_key_up=False):
			if force_key_up:
				raise OSError("blocked")

		with mock.patch.object(engine, "_send_key_event", side_effect=send):
			self.assertTrue(engine.play_macro([self._event()]))
			thread = engine._playback_thread
			if thread:
				thread.join(timeout=2)
		self.assertIn("Macro playback failed. See the NVDA log for details.", self.messages)
		self.assertNotIn("Macro playback completed.", self.messages)

	def test_unknown_unlocked_foreground_sends_no_input(self):
		self.module.get_foreground_app = lambda: None
		engine = self.module.MacroEngine()
		with mock.patch.object(engine.stop_playback_event, "wait", return_value=False):
			self.assertTrue(engine.play_macro([self._event()]))
			thread = engine._playback_thread
			if thread:
				thread.join(timeout=2)
		self.assertEqual([], self.user32.sent)

	def test_focus_change_during_long_wait_stops_promptly(self):
		app = ["target"]
		self.module.get_foreground_app = lambda: app[0]
		engine = self.module.MacroEngine()
		sent = threading.Event()
		original = engine._send_key_event

		def send(event, **kwargs):
			original(event, **kwargs)
			sent.set()

		engine._send_key_event = send
		self.assertTrue(
			engine.play_macro([self._event(), self._event("keyUp", delay=20)], target_app="target")
		)
		self.assertTrue(sent.wait(timeout=1))
		thread = engine._playback_thread
		app[0] = "other"
		thread.join(timeout=0.5)
		self.assertFalse(thread.is_alive())
		self.assertEqual(2, len(self.user32.sent))

	def test_trigger_release_wait_never_injects_user_key_release(self):
		engine = self.module.MacroEngine()
		self.user32.async_keys = {162}
		with mock.patch.object(
			engine.stop_playback_event, "wait", side_effect=lambda _delay: self.user32.async_keys.clear()
		):
			self.assertTrue(engine.wait_for_trigger_release())
		self.assertEqual([], self.user32.sent)

	def test_trigger_wait_observes_nvda_swallowed_modifier(self):
		engine = self.module.MacroEngine()
		modifiers = self.stubs["keyboardHandler"].currentModifiers
		modifiers.add((45, True))
		with mock.patch.object(
			engine.stop_playback_event, "wait", side_effect=lambda _delay: modifiers.clear()
		) as wait:
			self.assertTrue(engine.wait_for_trigger_release())
		wait.assert_called_once_with(0.01)

	def test_trigger_wait_can_be_canceled(self):
		engine = self.module.MacroEngine()
		self.user32.async_keys = {162}
		engine.stop_playback_event.set()
		self.assertFalse(engine.wait_for_trigger_release())
		self.assertEqual([], self.user32.sent)

	def test_trigger_wait_timeout_sends_no_input(self):
		engine = self.module.MacroEngine()
		self.user32.async_keys = {162}
		with (
			mock.patch.object(self.module.time, "perf_counter", side_effect=[0, 3]),
			self.assertRaises(OSError),
		):
			engine.wait_for_trigger_release()
		self.assertEqual([], self.user32.sent)

	def test_missing_key_up_is_released_before_each_loop(self):
		self.play([self._event()], loop_count=2, speed=0)
		self.assertEqual([False, True, False, True], [bool(flags & 2) for _vk, flags in self.user32.sent])

	def test_sixteen_simultaneous_starts_only_create_one_worker(self):
		engine = self.module.MacroEngine()
		barrier = threading.Barrier(16)
		results = []

		def start():
			barrier.wait(timeout=2)
			results.append(engine.play_macro([self._event(), self._event("keyUp", delay=10)]))

		requests = [threading.Thread(target=start) for _index in range(16)]
		for request in requests:
			request.start()
		for request in requests:
			request.join(timeout=3)
			self.assertFalse(request.is_alive())
		engine.shutdown()
		self.assertEqual(1, results.count(True))
		self.assertFalse(engine.is_playing)

	def test_infinite_wait_only_macro_is_cancellable(self):
		engine = self.module.MacroEngine()
		self.assertTrue(engine.play_macro([{"action": "delay", "delay": 20}], loop_count=0))
		engine.shutdown()
		self.assertFalse(engine.is_playing)
		self.assertEqual([], self.user32.sent)

	def test_speed_zero_skips_waits_in_finite_loops(self):
		self.play([self._event(delay=20), self._event("keyUp", delay=20)], loop_count=2, speed=0)
		self.assertEqual(4, len(self.user32.sent))

	def test_clipboard_round_trip_preserves_trailing_wait_and_start_delay(self):
		storage = self.module.MacroStorage()
		macro = storage.save_macro(
			"Wait",
			2,
			1.5,
			"target",
			"target",
			[self._event(), self._event("keyUp"), {"action": "delay", "delay": 1.7}],
			0.75,
		)
		clipboard = []
		self.stubs["api"].copyToClip = lambda text: clipboard.append(text) or True
		self.assertTrue(storage.export_macro_to_clipboard(0))
		self.stubs["api"].getClipData = lambda: clipboard[0]
		imported, _message = storage.import_macro_from_clipboard()
		self.assertTrue(imported)
		self.assertEqual(0.75, storage.macros[-1]["start_delay"])
		self.assertEqual(macro["events"], storage.macros[-1]["events"])

	def test_manager_remains_open_if_playback_is_rejected(self):
		manager = types.SimpleNamespace(
			macro_list=mock.Mock(),
			storage=types.SimpleNamespace(macros=[{"events": [self._event()]}]),
			engine=mock.Mock(),
			Destroy=mock.Mock(),
		)
		manager.macro_list.GetSelections.return_value = [0]
		manager.engine.play_macro.return_value = False
		self.module.MacroManagerDialog.on_play_click(manager, None)
		manager.Destroy.assert_not_called()

	def test_failed_edit_save_reopens_same_editor(self):
		dialog = mock.Mock()
		dialog.ShowModal.side_effect = [1, 2]
		manager = types.SimpleNamespace(
			macro_list=mock.Mock(), storage=mock.Mock(), active_app="target", refresh_list=mock.Mock()
		)
		manager.macro_list.GetSelections.return_value = [0]
		manager.storage.macros = [{"events": [self._event()]}]
		manager.storage.update_macro.side_effect = self.module.MacroStorageError("disk unavailable")
		with (
			mock.patch.object(self.module, "MacroEditDialog", return_value=dialog),
			mock.patch.object(self.module.wx, "ID_OK", 1, create=True),
		):
			self.module.MacroManagerDialog.on_edit_click(manager, None)
		self.assertEqual(2, dialog.ShowModal.call_count)
		dialog.Destroy.assert_called_once()
		manager.refresh_list.assert_not_called()

	def test_manager_delete_key_preserves_text_field(self):
		manager = types.SimpleNamespace(
			macro_list=object(), on_delete_click=mock.Mock(), on_close_click=mock.Mock()
		)
		event = mock.Mock()
		event.GetKeyCode.return_value = 127
		with (
			mock.patch.object(self.module.wx, "WXK_ESCAPE", 27, create=True),
			mock.patch.object(self.module.wx, "WXK_DELETE", 127, create=True),
			mock.patch.object(
				self.module.wx, "Window", types.SimpleNamespace(FindFocus=lambda: object()), create=True
			),
		):
			self.module.MacroManagerDialog.on_escape_press(manager, event)
		event.Skip.assert_called_once()
		manager.on_delete_click.assert_not_called()

	def test_macro_metadata_overflow_is_rejected(self):
		for field in ("speed", "start_delay"):
			macro = {"name": "Invalid", "events": [self._event()], field: 10**1000}
			with self.subTest(field=field), self.assertRaises(self.module.MacroValidationError):
				self.module.MacroStorage.normalize_macro(macro)
