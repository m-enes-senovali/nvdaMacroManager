import base64
import builtins
import copy
import ctypes
from ctypes import wintypes
import json
import math
import os
import re
import shutil
import tempfile
import threading
import time
from typing import Any, Callable
import uuid
import zlib

import addonHandler
import api
import appModuleHandler
import core
import globalPluginHandler
import globalVars
import gui
import logHandler
import scriptHandler
import ui
import winUser
import wx

addonHandler.initTranslation()
_: Callable[[str], str] = getattr(builtins, "_")

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
LLKHF_EXTENDED = 0x01
LLKHF_INJECTED = 0x10
VK_R = 0x52
NVDA_MODIFIER_KEYS = frozenset({20, 45, 96})
MAX_MACRO_EVENTS = 100_000
MAX_MACRO_NAME_LENGTH = 200
MAX_APP_NAME_LENGTH = 260
MAX_EVENT_DELAY_SECONDS = 3_600.0
MAX_START_DELAY_SECONDS = 3_600.0
MAX_PLAYBACK_SPEED = 100.0
MAX_LOOP_COUNT = 999
MAX_CLIPBOARD_TEXT_BYTES = 2 * 1024 * 1024
MAX_DECOMPRESSED_MACRO_BYTES = 10 * 1024 * 1024

user32 = ctypes.WinDLL("user32", use_last_error=True)


class KBDLLHOOKSTRUCT(ctypes.Structure):
	_fields_ = [
		("vkCode", wintypes.DWORD),
		("scanCode", wintypes.DWORD),
		("flags", wintypes.DWORD),
		("time", wintypes.DWORD),
		("dwExtraInfo", ctypes.c_size_t),
	]


HHOOK = wintypes.HANDLE
LRESULT = wintypes.LPARAM
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)


class KeyBdInput(ctypes.Structure):
	_fields_ = [
		("wVk", ctypes.c_ushort),
		("wScan", ctypes.c_ushort),
		("dwFlags", ctypes.c_ulong),
		("time", ctypes.c_ulong),
		("dwExtraInfo", ctypes.c_size_t),
	]


class HardwareInput(ctypes.Structure):
	_fields_ = [
		("uMsg", ctypes.c_ulong),
		("wParamL", ctypes.c_ushort),
		("wParamH", ctypes.c_ushort),
	]


class MouseInput(ctypes.Structure):
	_fields_ = [
		("dx", ctypes.c_long),
		("dy", ctypes.c_long),
		("mouseData", ctypes.c_ulong),
		("dwFlags", ctypes.c_ulong),
		("time", ctypes.c_ulong),
		("dwExtraInfo", ctypes.c_size_t),
	]


class Input_I(ctypes.Union):
	_fields_ = [
		("ki", KeyBdInput),
		("mi", MouseInput),
		("hi", HardwareInput),
	]


class Input(ctypes.Structure):
	_fields_ = [
		("type", ctypes.c_ulong),
		("ii", Input_I),
	]


user32.SetWindowsHookExW.argtypes = (ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD)
user32.SetWindowsHookExW.restype = HHOOK
user32.UnhookWindowsHookEx.argtypes = (HHOOK,)
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.CallNextHookEx.argtypes = (HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
user32.CallNextHookEx.restype = LRESULT
user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int)
user32.SendInput.restype = wintypes.UINT


def get_foreground_app():
	try:
		hwnd = winUser.getForegroundWindow()
		if not hwnd:
			return None
		threadID, processID = winUser.getWindowThreadProcessID(hwnd)
		return appModuleHandler.getAppNameFromProcessID(processID)
	except Exception as e:
		logHandler.log.debugWarning(f"Failed to get foreground app: {e}")
		return None


def get_key_name(vk, scan, ext):
	lparam = scan << 16
	if ext:
		lparam |= 1 << 24
	buf = ctypes.create_unicode_buffer(64)
	if user32.GetKeyNameTextW(lparam, buf, 64):
		return buf.value
	return f"VK_{vk}"


class MacroValidationError(ValueError):
	pass


class MacroStorageError(OSError):
	pass


def get_preferred_lock_app(macro_data):
	return macro_data.get("target_app") or macro_data.get("recorded_app")


def resolve_target_application(lock_enabled, preferred_app=None):
	if not lock_enabled:
		return None
	if preferred_app:
		return preferred_app
	current_app = get_foreground_app()
	if not current_app or current_app.casefold() == "nvda":
		raise MacroValidationError(
			_(
				"Cannot enable the application lock because no target application is available. "
				"Record the macro in the target application and try again.",
			),
		)
	return current_app


class MacroStorage:
	def __init__(self, update_scripts_callback=None):
		self.file_path = os.path.join(globalVars.appArgs.configPath, "nvda_macros.json")
		self.backup_path = f"{self.file_path}.bak"
		self.update_scripts_callback = update_scripts_callback
		self._database_needs_repair = False
		self.macros = self.load_macros()
		if self._database_needs_repair:
			try:
				self._write_to_file()
			except MacroStorageError:
				logHandler.log.error("NVDAMacroManager: Could not persist repaired macro data")

	@staticmethod
	def _normalize_optional_app(value: Any, field_name: str) -> str | None:
		if value is None or value == "":
			return None
		if not isinstance(value, str) or len(value) > MAX_APP_NAME_LENGTH:
			raise MacroValidationError(f"{field_name} must be a short string or null")
		return value

	@staticmethod
	def _normalize_event(event: Any) -> dict[str, Any]:
		if not isinstance(event, dict):
			raise MacroValidationError("Each macro event must be an object")
		action = event.get("action")
		if action not in {"keyDown", "keyUp"}:
			raise MacroValidationError("Event action must be keyDown or keyUp")
		vk_code = event.get("vkCode")
		scan_code = event.get("scanCode", 0)
		delay = event.get("delay", 0.0)
		if isinstance(vk_code, bool) or not isinstance(vk_code, int) or not 1 <= vk_code <= 0xFF:
			raise MacroValidationError("Event vkCode must be an integer from 1 to 255")
		if isinstance(scan_code, bool) or not isinstance(scan_code, int) or not 0 <= scan_code <= 0xFFFF:
			raise MacroValidationError("Event scanCode must be an integer from 0 to 65535")
		if isinstance(delay, bool) or not isinstance(delay, (int, float)):
			raise MacroValidationError("Event delay must be numeric")
		delay = float(delay)
		if not math.isfinite(delay) or not 0 <= delay <= MAX_EVENT_DELAY_SECONDS:
			raise MacroValidationError("Event delay is outside the supported range")
		return {
			"action": action,
			"vkCode": vk_code,
			"scanCode": scan_code,
			"extended": bool(event.get("extended", False)),
			"delay": delay,
		}

	@classmethod
	def normalize_macro(cls, macro: Any, *, new_id: bool = False) -> dict[str, Any]:
		if not isinstance(macro, dict):
			raise MacroValidationError("Macro must be an object")
		name = macro.get("name")
		if not isinstance(name, str) or not name.strip() or len(name.strip()) > MAX_MACRO_NAME_LENGTH:
			raise MacroValidationError("Macro name is missing or too long")
		events = macro.get("events")
		if not isinstance(events, list) or len(events) > MAX_MACRO_EVENTS:
			raise MacroValidationError("Macro events must be a bounded list")
		loop_count = macro.get("loop_count", 1)
		if (
			isinstance(loop_count, bool)
			or not isinstance(loop_count, int)
			or not 0 <= loop_count <= MAX_LOOP_COUNT
		):
			raise MacroValidationError("Loop count is outside the supported range")
		speed = macro.get("speed", 1.0)
		if isinstance(speed, bool) or not isinstance(speed, (int, float)):
			raise MacroValidationError("Playback speed must be numeric")
		speed = float(speed)
		if not math.isfinite(speed) or not 0 <= speed <= MAX_PLAYBACK_SPEED:
			raise MacroValidationError("Playback speed is outside the supported range")
		start_delay = macro.get("start_delay", 0.0)
		if isinstance(start_delay, bool) or not isinstance(start_delay, (int, float)):
			raise MacroValidationError("Start delay must be numeric")
		start_delay = float(start_delay)
		if not math.isfinite(start_delay) or not 0 <= start_delay <= MAX_START_DELAY_SECONDS:
			raise MacroValidationError("Start delay is outside the supported range")
		macro_id = macro.get("id")
		if new_id or not isinstance(macro_id, str) or not macro_id.strip() or len(macro_id) > 100:
			macro_id = uuid.uuid4().hex
		return {
			"id": macro_id,
			"name": name.strip(),
			"loop_count": loop_count,
			"speed": speed,
			"start_delay": start_delay,
			"target_app": cls._normalize_optional_app(macro.get("target_app"), "target_app"),
			"recorded_app": cls._normalize_optional_app(macro.get("recorded_app"), "recorded_app"),
			"events": [cls._normalize_event(event) for event in events],
		}

	def load_macros(self):
		if not os.path.exists(self.file_path):
			return []
		try:
			if os.path.getsize(self.file_path) > MAX_DECOMPRESSED_MACRO_BYTES:
				raise MacroValidationError("Macro database is too large")
			with open(self.file_path, "r", encoding="utf-8") as f:
				data = json.load(f)
			if not isinstance(data, list):
				raise MacroValidationError("Macro data is not a list")
			valid_macros = []
			seen_ids = set()
			for index, macro in enumerate(data):
				try:
					normalized = self.normalize_macro(macro)
					if normalized["id"] in seen_ids:
						normalized["id"] = uuid.uuid4().hex
					if normalized != macro:
						self._database_needs_repair = True
					seen_ids.add(normalized["id"])
					valid_macros.append(normalized)
				except MacroValidationError as error:
					self._database_needs_repair = True
					logHandler.log.error(
						f"NVDAMacroManager: Ignoring invalid macro at index {index}: {error}"
					)
			return valid_macros
		except Exception as error:
			logHandler.log.error(f"NVDAMacroManager: Macro loading error: {error}")
		return []

	def _notify_scripts_changed(self):
		if self.update_scripts_callback:
			self.update_scripts_callback()

	def save_macro(self, name, loop_count, speed, target_app, recorded_app, events, start_delay=0.0):
		new_macro = self.normalize_macro(
			{
				"name": name,
				"loop_count": loop_count,
				"speed": speed,
				"start_delay": start_delay,
				"target_app": target_app,
				"recorded_app": recorded_app,
				"events": events,
			},
			new_id=True,
		)
		self.macros.append(new_macro)
		try:
			self._write_to_file()
		except Exception:
			self.macros.pop()
			raise
		self._notify_scripts_changed()
		return new_macro

	def update_macro(self, index, updated_data):
		if not 0 <= index < len(self.macros):
			return False
		old_macro = self.macros[index]
		candidate = copy.deepcopy(old_macro)
		candidate.update(updated_data)
		candidate["id"] = old_macro["id"]
		self.macros[index] = self.normalize_macro(candidate)
		try:
			self._write_to_file()
		except Exception:
			self.macros[index] = old_macro
			raise
		self._notify_scripts_changed()
		return True

	def delete_macro(self, index):
		if not 0 <= index < len(self.macros):
			return None
		deleted_macro = self.macros.pop(index)
		try:
			self._write_to_file()
		except Exception:
			self.macros.insert(index, deleted_macro)
			raise
		self._notify_scripts_changed()
		return deleted_macro["name"]

	def delete_macros(self, indices):
		valid_indices = sorted({index for index in indices if 0 <= index < len(self.macros)}, reverse=True)
		if not valid_indices:
			return []
		old_macros = self.macros[:]
		deleted_names = [self.macros[index]["name"] for index in valid_indices]
		for index in valid_indices:
			self.macros.pop(index)
		try:
			self._write_to_file()
		except Exception:
			self.macros = old_macros
			raise
		self._notify_scripts_changed()
		return deleted_names

	def import_macro(self, imported_data):
		macro = self.normalize_macro(imported_data, new_id=True)
		self.macros.append(macro)
		try:
			self._write_to_file()
		except Exception:
			self.macros.pop()
			raise
		self._notify_scripts_changed()
		return macro

	def export_macro_to_clipboard(self, index):
		if not 0 <= index < len(self.macros):
			return False
		macro = self.macros[index]
		json_str = json.dumps(macro, ensure_ascii=False)
		compressed = zlib.compress(json_str.encode("utf-8"))
		b64_str = base64.b64encode(compressed).decode("ascii")
		return bool(api.copyToClip(f"NVDAMacro::{b64_str}"))

	def import_macro_from_clipboard(self):
		try:
			text = api.getClipData()
			if not isinstance(text, str) or not text.startswith("NVDAMacro::"):
				return False, _("No valid macro code found in clipboard.")
			if len(text.encode("utf-8")) > MAX_CLIPBOARD_TEXT_BYTES:
				raise MacroValidationError("Clipboard macro is too large")
			b64_str = text.split("::", 1)[1].strip()
			compressed = base64.b64decode(b64_str, validate=True)
			decompressor = zlib.decompressobj()
			payload = decompressor.decompress(compressed, MAX_DECOMPRESSED_MACRO_BYTES + 1)
			if decompressor.unconsumed_tail or len(payload) > MAX_DECOMPRESSED_MACRO_BYTES:
				raise MacroValidationError("Decompressed macro is too large")
			payload += decompressor.flush()
			if not decompressor.eof or len(payload) > MAX_DECOMPRESSED_MACRO_BYTES:
				raise MacroValidationError("Compressed macro data is incomplete or too large")
			imported_data = json.loads(payload.decode("utf-8"))
			macro = self.import_macro(imported_data)
			return True, macro["name"]
		except (MacroValidationError, ValueError, TypeError, json.JSONDecodeError, zlib.error) as error:
			logHandler.log.error(f"NVDAMacroManager: Clipboard import rejected: {error}")
			return False, _("Invalid macro format in clipboard.")
		except Exception as error:
			logHandler.log.error(f"NVDAMacroManager: Clipboard import error: {error}")
			return False, _("Failed to decode macro from clipboard.")

	def _write_to_file(self):
		config_dir = os.path.dirname(self.file_path)
		os.makedirs(config_dir, exist_ok=True)
		temp_path = None
		try:
			with tempfile.NamedTemporaryFile(
				"w",
				encoding="utf-8",
				dir=config_dir,
				prefix="nvda_macros_",
				suffix=".tmp",
				delete=False,
			) as temp_file:
				temp_path = temp_file.name
				json.dump(self.macros, temp_file, ensure_ascii=False, indent=4)
				temp_file.flush()
				os.fsync(temp_file.fileno())
			if os.path.exists(self.file_path):
				shutil.copy2(self.file_path, self.backup_path)
			os.replace(temp_path, self.file_path)
		except Exception as error:
			if temp_path and os.path.exists(temp_path):
				try:
					os.unlink(temp_path)
				except OSError:
					pass
			logHandler.log.error(f"NVDAMacroManager: Macro saving error: {error}")
			raise MacroStorageError(str(error)) from error


class MacroEngine:
	def __init__(self, safe_stop_callback=None):
		self.is_recording = False
		self.is_playing = False
		self.safe_mode = False
		self.events = []
		self.last_time = 0.0
		self.hook_id = None
		self._hook_proc = HOOKPROC(self.low_level_keyboard_handler)
		self.recorded_app = None
		self.stop_playback_event = threading.Event()
		self._safe_stop_callback = safe_stop_callback
		self._safe_stop_requested = False
		self._playback_thread = None
		self._state_lock = threading.RLock()

	def start_recording(self, safe_mode=False):
		with self._state_lock:
			if self.is_recording or self.is_playing:
				return False
			try:
				hook_id = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._hook_proc, None, 0)
			except OSError as error:
				logHandler.log.error(f"NVDAMacroManager: Failed to install the keyboard hook: {error}")
				return False
			if not hook_id:
				logHandler.log.error("NVDAMacroManager: Failed to install the low-level keyboard hook")
				return False
			self.events = []
			self.is_recording = True
			self.safe_mode = bool(safe_mode)
			self.last_time = time.perf_counter()
			self.hook_id = hook_id
			self.recorded_app = get_foreground_app()
			self._safe_stop_requested = False
		return True

	def stop_recording(self):
		with self._state_lock:
			self.is_recording = False
			hook_id = self.hook_id
			self.hook_id = None
			self._safe_stop_requested = False
		if hook_id:
			try:
				if not user32.UnhookWindowsHookEx(hook_id):
					logHandler.log.error("NVDAMacroManager: Failed to remove the low-level keyboard hook")
			except OSError as error:
				logHandler.log.error(f"NVDAMacroManager: Failed to remove the keyboard hook: {error}")
		if self.recorded_app is None:
			self.recorded_app = get_foreground_app()

		while self.events and self.events[0]["action"] == "keyUp":
			self.events.pop(0)

		if self.events:
			modifiers = {16, 17, 18, 20, 45, 91, 92, 96, 160, 161, 162, 163, 164, 165}
			cut_index = len(self.events)
			trigger_vk = None

			for i in range(len(self.events) - 1, -1, -1):
				e = self.events[i]
				vk = e["vkCode"]
				if vk not in modifiers:
					if trigger_vk is None:
						trigger_vk = vk
					elif trigger_vk != vk:
						break
				cut_index = i
				if e["delay"] > 0.5:
					break
			self.events = self.events[:cut_index]

		pressed_keys = {}
		for e in self.events:
			key_id = (e["vkCode"], e["scanCode"], e.get("extended", False))
			if e["action"] == "keyDown":
				pressed_keys[key_id] = e
			elif e["action"] == "keyUp":
				pressed_keys.pop(key_id, None)

		for e in pressed_keys.values():
			self.events.append(
				{
					"action": "keyUp",
					"vkCode": e["vkCode"],
					"scanCode": e["scanCode"],
					"extended": e["extended"],
					"delay": 0.05,
				},
			)
		return copy.deepcopy(self.events), self.recorded_app

	def low_level_keyboard_handler(self, nCode, wParam, lParam):
		try:
			return self._low_level_keyboard_handler_impl(nCode, wParam, lParam)
		except Exception as error:
			logHandler.log.error(f"NVDAMacroManager: Keyboard hook error: {error}")
			return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

	def _low_level_keyboard_handler_impl(self, nCode, wParam, lParam):
		if nCode >= 0 and self.is_recording:
			keyboard_data = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
			injected = bool(keyboard_data.flags & LLKHF_INJECTED)
			if not injected:
				if wParam not in (WM_KEYDOWN, WM_SYSKEYDOWN, WM_KEYUP, WM_SYSKEYUP):
					return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)
				current_time = time.perf_counter()
				delay = current_time - self.last_time
				action = "keyDown" if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN) else "keyUp"
				vk = keyboard_data.vkCode
				self.events.append(
					{
						"action": action,
						"vkCode": vk,
						"scanCode": keyboard_data.scanCode,
						"extended": bool(keyboard_data.flags & LLKHF_EXTENDED),
						"delay": delay,
					},
				)
				self.last_time = current_time

				if self.safe_mode:
					is_stop_gesture = (
						action == "keyDown"
						and vk == VK_R
						and any(user32.GetAsyncKeyState(key) & 0x8000 for key in NVDA_MODIFIER_KEYS)
						and bool(user32.GetAsyncKeyState(16) & 0x8000)
						and bool(
							user32.GetAsyncKeyState(91) & 0x8000 or user32.GetAsyncKeyState(92) & 0x8000,
						)
					)
					if is_stop_gesture and not self._safe_stop_requested and self._safe_stop_callback:
						self._safe_stop_requested = True
						core.callLater(0, self._safe_stop_callback)
					return 1
		return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

	@staticmethod
	def _queue_message(message):
		core.callLater(0, ui.message, message)

	@staticmethod
	def _target_matches(target_app):
		if not target_app:
			return True, get_foreground_app()
		current_app = get_foreground_app()
		return bool(current_app and current_app.casefold() == target_app.casefold()), current_app

	@staticmethod
	def _send_key_event(event, *, force_key_up=False):
		inp = Input()
		inp.type = INPUT_KEYBOARD
		inp.ii.ki.wVk = event["vkCode"]
		inp.ii.ki.wScan = event["scanCode"]
		flags = KEYEVENTF_EXTENDEDKEY if event.get("extended", False) else 0
		if force_key_up or event["action"] == "keyUp":
			flags |= KEYEVENTF_KEYUP
		inp.ii.ki.dwFlags = flags
		inp.ii.ki.time = 0
		inp.ii.ki.dwExtraInfo = 0
		if user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(Input)) != 1:
			raise OSError(ctypes.get_last_error(), "SendInput failed")

	def _release_injected_keys(self, pressed_keys):
		for event in reversed(list(pressed_keys.values())):
			try:
				self._send_key_event(event, force_key_up=True)
			except OSError as error:
				logHandler.log.error(f"NVDAMacroManager: Failed to release an injected key: {error}")

	def play_macro(self, events_to_play, loop_count=1, speed=1.0, target_app=None, start_delay=0.0):
		try:
			events = [MacroStorage._normalize_event(event) for event in events_to_play]
			if not events or len(events) > MAX_MACRO_EVENTS:
				raise MacroValidationError("Macro has no playable events")
			if (
				isinstance(loop_count, bool)
				or not isinstance(loop_count, int)
				or not 0 <= loop_count <= MAX_LOOP_COUNT
			):
				raise MacroValidationError("Invalid loop count")
			if isinstance(speed, bool) or not isinstance(speed, (int, float)):
				raise MacroValidationError("Invalid playback speed")
			speed = float(speed)
			if not math.isfinite(speed) or not 0 <= speed <= MAX_PLAYBACK_SPEED:
				raise MacroValidationError("Invalid playback speed")
			if isinstance(start_delay, bool) or not isinstance(start_delay, (int, float)):
				raise MacroValidationError("Invalid start delay")
			start_delay = float(start_delay)
			if not math.isfinite(start_delay) or not 0 <= start_delay <= MAX_START_DELAY_SECONDS:
				raise MacroValidationError("Invalid start delay")
			target_app = MacroStorage._normalize_optional_app(target_app, "target_app")
		except (MacroValidationError, TypeError) as error:
			logHandler.log.error(f"NVDAMacroManager: Refusing to play an invalid macro: {error}")
			self._queue_message(_("Cannot play this macro because its data is invalid."))
			return False

		with self._state_lock:
			if self.is_playing or self.is_recording:
				message = (
					_("Please stop recording first.")
					if self.is_recording
					else _("A macro is already playing.")
				)
				self._queue_message(message)
				return False
			self.is_playing = True
			self.stop_playback_event.clear()

		def playback_thread():
			pressed_keys = {}
			completion_message = None
			try:
				for attempt in range(40):
					if self.stop_playback_event.is_set():
						break
					current_app = get_foreground_app()
					if not current_app or current_app.casefold() != "nvda":
						break
					self.stop_playback_event.wait(0.05)

				target_matches, current_app = self._target_matches(target_app)
				if not target_matches:
					completion_message = _(
						"Security Warning: Macro locked to '{target_app}'. Current: '{current_app}'.",
					).format(target_app=target_app, current_app=current_app or _("unknown"))
					return

				if start_delay > 0 and self.stop_playback_event.wait(start_delay):
					return

				target_matches, current_app = self._target_matches(target_app)
				if not target_matches:
					completion_message = _(
						"Macro stopped because the active application changed. Expected: "
						"'{target_app}', current: '{current_app}'.",
					).format(target_app=target_app, current_app=current_app or _("unknown"))
					return

				loop_idx = 0
				while not self.stop_playback_event.is_set() and (loop_count == 0 or loop_idx < loop_count):
					for event in events:
						if self.stop_playback_event.is_set():
							break
						actual_delay = 0.005 if speed <= 0 else event["delay"] / speed
						if event["action"] == "keyUp" and actual_delay < 0.035:
							actual_delay = 0.035
						if actual_delay > 0 and self.stop_playback_event.wait(actual_delay):
							break
						target_matches, current_app = self._target_matches(target_app)
						if not target_matches:
							completion_message = _(
								"Macro stopped because the active application changed. Expected: "
								"'{target_app}', current: '{current_app}'.",
							).format(target_app=target_app, current_app=current_app or _("unknown"))
							self.stop_playback_event.set()
							break

						self._send_key_event(event)
						key_id = (event["vkCode"], event["scanCode"], event["extended"])
						if event["action"] == "keyDown":
							pressed_keys[key_id] = event
						else:
							pressed_keys.pop(key_id, None)
					if not self.stop_playback_event.is_set():
						self.stop_playback_event.wait(0.1)
					loop_idx += 1
			except Exception as error:
				logHandler.log.error(f"NVDAMacroManager: Macro playback error: {error}")
				completion_message = _("Macro playback failed. See the NVDA log for details.")
			finally:
				self._release_injected_keys(pressed_keys)
				with self._state_lock:
					self.is_playing = False
					self._playback_thread = None
				if completion_message:
					self._queue_message(completion_message)
				elif self.stop_playback_event.is_set():
					self._queue_message(_("Macro playback canceled."))
				else:
					self._queue_message(_("Macro playback completed."))

		thread = threading.Thread(target=playback_thread)
		thread.daemon = True
		with self._state_lock:
			self._playback_thread = thread
		try:
			thread.start()
		except Exception as error:
			with self._state_lock:
				self.is_playing = False
				self._playback_thread = None
			logHandler.log.error(f"NVDAMacroManager: Failed to start playback thread: {error}")
			self._queue_message(_("Macro playback failed. See the NVDA log for details."))
			return False
		return True

	def shutdown(self):
		self.stop_playback_event.set()
		if self.is_recording or self.hook_id:
			self.stop_recording()
		thread = self._playback_thread
		if thread and thread is not threading.current_thread():
			thread.join(timeout=1.0)


class KeyCaptureDialog(wx.Dialog):
	def __init__(self, parent):
		super(KeyCaptureDialog, self).__init__(
			parent,
			title=_("Press a New Key"),
			size=(350, 150),
			style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP,
		)
		self.captured_vk = None
		self.captured_scan = None
		self.captured_ext = False

		sizer = wx.BoxSizer(wx.VERTICAL)
		lbl = wx.StaticText(
			self,
			label=_("Please press the new key on your keyboard...\n(It will be captured automatically)"),
		)
		lbl.Wrap(300)
		sizer.Add(lbl, 1, wx.ALL | wx.ALIGN_CENTER, 20)

		self.SetSizer(sizer)
		self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
		self.CenterOnParent()

	def on_key(self, event):
		raw_vk = event.GetRawKeyCode()
		raw_flags = event.GetRawKeyFlags()

		if raw_vk:
			self.captured_vk = raw_vk
			self.captured_scan = (raw_flags >> 16) & 0xFF
			self.captured_ext = (raw_flags >> 24) & 1 == 1
		else:
			self.captured_vk = event.GetKeyCode()
			self.captured_scan = 0
			self.captured_ext = False

		self.EndModal(wx.ID_OK)


class KeySelectDialog(wx.Dialog):
	@classmethod
	def get_dynamic_vk_mapping(cls):
		options = []
		user32 = ctypes.windll.user32

		letters_map = {}
		for vk in range(65, 91):
			letters_map[chr(vk)] = vk

		sym_map = {
			".": _(". (Dot)"),
			",": _(", (Comma)"),
			"-": _("- (Hyphen / Minus)"),
			'"': _('" (Double quote)'),
			"<": _("< (Less than)"),
			">": _("> (Greater than)"),
			";": _("; (Semicolon)"),
			":": _(": (Colon)"),
			"'": _("' (Single quote)"),
			"`": _("` (Grave accent)"),
			"~": _("~ (Tilde)"),
			"=": _("= (Equals)"),
			"+": _("+ (Plus)"),
			"[": _("[ (Left square bracket)"),
			"]": _("] (Right square bracket)"),
			"{": _("{ (Left brace)"),
			"}": _("} (Right brace)"),
			"\\": _("\\ (Backslash)"),
			"/": _("/ (Slash)"),
			"|": _("| (Vertical bar)"),
			"?": _("? (Question mark)"),
			"!": _("! (Exclamation mark)"),
			"@": _("@ (At sign)"),
			"#": _("# (Number sign)"),
			"$": _("$ (Dollar sign)"),
			"%": _("% (Percent sign)"),
			"^": _("^ (Caret)"),
			"&": _("& (Ampersand)"),
			"*": _("* (Asterisk)"),
			"(": _("( (Left parenthesis)"),
			")": _(") (Right parenthesis)"),
			"_": _("_ (Underscore)"),
		}

		local_chars = []
		for vk in range(186, 223):
			char_val = user32.MapVirtualKeyW(vk, 2) & 0xFFFF
			if char_val > 0:
				try:
					char_str = chr(char_val)
					if char_str == "i":
						char_str = "İ"
					elif char_str == "ı":
						char_str = "I"
					elif char_str == "ğ":
						char_str = "Ğ"
					elif char_str == "ü":
						char_str = "Ü"
					elif char_str == "ş":
						char_str = "Ş"
					elif char_str == "ö":
						char_str = "Ö"
					elif char_str == "ç":
						char_str = "Ç"
					else:
						char_str = char_str.upper()

					if char_str.strip():
						if char_str.isalpha():
							letters_map[char_str] = vk
						else:
							display_name = sym_map.get(char_str, char_str)
							local_chars.append((display_name, vk))
				except ValueError:
					pass

		def char_sort_key(char):
			order = "ABCÇDEFGĞHIİJKLMNOÖPQRSŞTUÜVWXYZ"
			return order.index(char) if char in order else 1000 + ord(char)

		sorted_letters = sorted(letters_map.items(), key=lambda item: char_sort_key(item[0]))
		options.append((f"--- {_('Letters')} ---", 0))
		options.extend(sorted_letters)

		if local_chars:
			local_chars.sort(key=lambda x: x[0])
			options.append((f"--- {_('Punctuation')} ---", 0))
			options.extend(local_chars)

		options.append((f"--- {_('Numbers')} ---", 0))
		for vk in range(48, 58):
			options.append((chr(vk), vk))

		options.append((f"--- {_('Numpad')} ---", 0))
		for i in range(10):
			options.append((f"Numpad {i}", 96 + i))
		options.extend(
			[
				(_("Numpad Multiply"), 106),
				(_("Numpad Add"), 107),
				(_("Numpad Subtract"), 109),
				(_("Numpad Decimal"), 110),
				(_("Numpad Divide"), 111),
			],
		)

		options.append((f"--- {_('Function keys')} ---", 0))
		for i in range(1, 13):
			options.append((f"F{i}", 111 + i))

		options.append((f"--- {_('Navigation')} ---", 0))
		options.extend(
			[
				(_("Left Arrow"), 37),
				(_("Up Arrow"), 38),
				(_("Right Arrow"), 39),
				(_("Down Arrow"), 40),
				(_("Page Up"), 33),
				(_("Page Down"), 34),
				(_("Home"), 36),
				(_("End"), 35),
			],
		)

		options.append((f"--- {_('System and editing')} ---", 0))
		options.extend(
			[
				(_("Backspace"), 8),
				(_("Tab"), 9),
				(_("Enter"), 13),
				(_("Space"), 32),
				(_("Insert"), 45),
				(_("Delete"), 46),
				(_("Escape"), 27),
				(_("Shift"), 16),
				(_("Ctrl"), 17),
				(_("Alt"), 18),
				(_("Windows"), 91),
				(_("Application key"), 93),
				(_("Caps Lock"), 20),
				(_("Num Lock"), 144),
				(_("Scroll Lock"), 145),
				(_("Pause"), 19),
				(_("Print Screen"), 44),
			],
		)
		return options

	def __init__(self, parent):
		super(KeySelectDialog, self).__init__(
			parent,
			title=_("Edit Key"),
			size=(350, 250),
			style=wx.DEFAULT_DIALOG_STYLE,
		)
		self.captured_vk = None
		self.captured_scan = 0
		self.captured_ext = False
		self.VK_OPTIONS = self.get_dynamic_vk_mapping()

		main_sizer = wx.BoxSizer(wx.VERTICAL)

		lbl_auto = wx.StaticText(self, label=_("Option 1: Auto Capture"))
		main_sizer.Add(lbl_auto, 0, wx.ALL, 10)

		self.btn_capture = wx.Button(self, label=_("Press to Capture"))
		self.btn_capture.Bind(wx.EVT_BUTTON, self.on_capture_click)
		main_sizer.Add(self.btn_capture, 0, wx.ALL | wx.EXPAND, 10)

		main_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 10)

		lbl_manual = wx.StaticText(self, label=_("Option 2: Select from List"))
		main_sizer.Add(lbl_manual, 0, wx.ALL, 10)

		choices = [item[0] for item in self.VK_OPTIONS]
		self.key_combo = wx.Choice(self, choices=choices)
		self.key_combo.SetSelection(0)
		main_sizer.Add(self.key_combo, 0, wx.ALL | wx.EXPAND, 10)

		btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.btn_save_combo = wx.Button(self, wx.ID_OK, label=_("Save Selected Key"))
		self.btn_save_combo.Bind(wx.EVT_BUTTON, self.on_save_combo)
		self.btn_cancel = wx.Button(self, wx.ID_CANCEL, label=_("Cancel"))

		btn_sizer.Add(self.btn_save_combo, 0, wx.ALL, 5)
		btn_sizer.Add(self.btn_cancel, 0, wx.ALL, 5)
		main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER)

		self.SetSizer(main_sizer)
		self.CenterOnParent()

	def on_capture_click(self, event):
		dlg = KeyCaptureDialog(self)
		if dlg.ShowModal() == wx.ID_OK and dlg.captured_vk:
			self.captured_vk = dlg.captured_vk
			self.captured_scan = dlg.captured_scan
			self.captured_ext = dlg.captured_ext
			dlg.Destroy()
			self.EndModal(wx.ID_OK)
		else:
			dlg.Destroy()

	def on_save_combo(self, event):
		idx = self.key_combo.GetSelection()
		if idx != wx.NOT_FOUND:
			vk = self.VK_OPTIONS[idx][1]
			if vk != 0:
				self.captured_vk = vk
				self.captured_scan = 0
				self.captured_ext = False
				self.EndModal(wx.ID_OK)
				return
		ui.message(_("Please select a valid key from the list."))


class AddEventDialog(wx.Dialog):
	def __init__(self, parent):
		super(AddEventDialog, self).__init__(
			parent,
			title=_("Add Event"),
			size=(400, 350),
			style=wx.DEFAULT_DIALOG_STYLE,
		)
		self.new_event = None
		self.VK_OPTIONS = KeySelectDialog.get_dynamic_vk_mapping()

		main_sizer = wx.BoxSizer(wx.VERTICAL)

		main_sizer.Add(wx.StaticText(self, label=_("Event Type:")), 0, wx.ALL, 10)
		self.type_choices = [
			_("Press"),
			_("Key Down"),
			_("Key Up"),
			_("Wait"),
		]
		self.type_values = ["press", "keyDown", "keyUp", "delay"]
		self.type_combo = wx.Choice(self, choices=self.type_choices)
		self.type_combo.SetSelection(0)
		self.type_combo.Bind(wx.EVT_CHOICE, self.on_type_change)
		main_sizer.Add(self.type_combo, 0, wx.ALL | wx.EXPAND, 10)

		main_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 10)

		self.wait_panel = wx.Panel(self)
		wait_sizer = wx.BoxSizer(wx.VERTICAL)
		wait_sizer.Add(
			wx.StaticText(
				self.wait_panel,
				label=_("Delay in milliseconds (ms):\n(Example: 1000 for 1 second)"),
			),
			0,
			wx.ALL,
			5,
		)
		self.delay_ctrl = wx.TextCtrl(self.wait_panel, value="100")
		wait_sizer.Add(self.delay_ctrl, 0, wx.ALL | wx.EXPAND, 5)
		self.wait_panel.SetSizer(wait_sizer)

		self.key_panel = wx.Panel(self)
		key_sizer = wx.BoxSizer(wx.VERTICAL)
		key_sizer.Add(wx.StaticText(self.key_panel, label=_("Option 1: Auto Capture")), 0, wx.ALL, 5)
		self.btn_capture = wx.Button(self.key_panel, label=_("Press to Capture"))
		self.btn_capture.Bind(wx.EVT_BUTTON, self.on_capture_click)
		key_sizer.Add(self.btn_capture, 0, wx.ALL | wx.EXPAND, 5)

		key_sizer.Add(wx.StaticText(self.key_panel, label=_("Option 2: Select from List")), 0, wx.ALL, 5)
		combo_choices = [item[0] for item in self.VK_OPTIONS]
		self.key_combo = wx.Choice(self.key_panel, choices=combo_choices)
		self.key_combo.SetSelection(0)
		key_sizer.Add(self.key_combo, 0, wx.ALL | wx.EXPAND, 5)
		self.key_panel.SetSizer(key_sizer)

		main_sizer.Add(self.wait_panel, 0, wx.EXPAND | wx.ALL, 5)
		main_sizer.Add(self.key_panel, 0, wx.EXPAND | wx.ALL, 5)

		btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.btn_save = wx.Button(self, wx.ID_OK, label=_("Add Event"))
		self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
		self.btn_cancel = wx.Button(self, wx.ID_CANCEL, label=_("Cancel"))
		btn_sizer.Add(self.btn_save, 0, wx.ALL, 5)
		btn_sizer.Add(self.btn_cancel, 0, wx.ALL, 5)
		main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER)

		self.SetSizer(main_sizer)
		self.update_visibility()
		self.CenterOnParent()

	def on_type_change(self, event):
		self.update_visibility()

	def update_visibility(self):
		sel_type = self.type_values[self.type_combo.GetSelection()]
		if sel_type == "delay":
			self.wait_panel.Show()
			self.key_panel.Hide()
		else:
			self.wait_panel.Hide()
			self.key_panel.Show()
		self.Layout()

	def on_capture_click(self, event):
		dlg = KeyCaptureDialog(self)
		if dlg.ShowModal() == wx.ID_OK and dlg.captured_vk:
			self.new_event = {
				"type": self.type_values[self.type_combo.GetSelection()],
				"vkCode": dlg.captured_vk,
				"scanCode": dlg.captured_scan,
				"extended": dlg.captured_ext,
			}
			if self.new_event["type"] == "press":
				self.new_event["hold"] = 0.035
			dlg.Destroy()
			self.EndModal(wx.ID_OK)
		else:
			dlg.Destroy()

	def on_save(self, event):
		sel_type = self.type_values[self.type_combo.GetSelection()]
		if sel_type == "delay":
			val = self.delay_ctrl.GetValue().strip()
			if val.isdigit():
				self.new_event = {"type": "delay", "delay": int(val) / 1000.0}
				self.EndModal(wx.ID_OK)
			else:
				ui.message(_("Error: Please enter numbers only."))
		else:
			idx = self.key_combo.GetSelection()
			if idx != wx.NOT_FOUND:
				vk = self.VK_OPTIONS[idx][1]
				if vk != 0:
					self.new_event = {
						"type": sel_type,
						"vkCode": vk,
						"scanCode": 0,
						"extended": False,
					}
					if sel_type == "press":
						self.new_event["hold"] = 0.035
					self.EndModal(wx.ID_OK)
					return
			ui.message(_("Please select a valid key from the list."))


class MacroEditDialog(wx.Dialog):
	def __init__(self, parent, macro_data):
		super(MacroEditDialog, self).__init__(parent, title=_("Edit Macro (IDE)"), size=(600, 680))
		self.macro_data = macro_data
		original_events = copy.deepcopy(macro_data.get("events", []))
		self.linear_events = self._linearize_events(original_events)

		self.undo_stack = []
		self.redo_stack = []
		self.clipboard_events = []

		main_sizer = wx.BoxSizer(wx.VERTICAL)
		grid_sizer = wx.FlexGridSizer(5, 2, 5, 5)
		grid_sizer.AddGrowableCol(1)

		grid_sizer.Add(wx.StaticText(self, label=_("Macro Name:")), 0, wx.ALIGN_CENTER_VERTICAL)
		self.name_text = wx.TextCtrl(self, value=macro_data["name"])
		self.name_text.SetName(_("Macro Name"))
		grid_sizer.Add(self.name_text, 1, wx.EXPAND)

		grid_sizer.Add(wx.StaticText(self, label=_("Loop:")), 0, wx.ALIGN_CENTER_VERTICAL)
		loop_box = wx.BoxSizer(wx.HORIZONTAL)
		is_infinite = macro_data.get("loop_count", 1) == 0
		self.loop_spin = wx.SpinCtrl(
			self,
			value=str(macro_data.get("loop_count", 1) if not is_infinite else 1),
			min=1,
			max=999,
		)
		self.loop_spin.SetName(_("Loop Count"))
		self.loop_spin.Enable(not is_infinite)
		loop_box.Add(self.loop_spin, 0, wx.RIGHT, 10)
		self.infinite_check = wx.CheckBox(self, label=_("Run until stopped"))
		self.infinite_check.SetName(_("Run until stopped (Infinite Loop)"))
		self.infinite_check.SetValue(is_infinite)
		self.infinite_check.Bind(wx.EVT_CHECKBOX, self.on_infinite_toggle)
		loop_box.Add(self.infinite_check, 0, wx.ALIGN_CENTER_VERTICAL)
		grid_sizer.Add(loop_box, 1, wx.EXPAND)

		grid_sizer.Add(
			wx.StaticText(self, label=_("Playback Speed Multiplier (0 = Instant):")),
			0,
			wx.ALIGN_CENTER_VERTICAL,
		)
		self.speed_choices = ["0", "0.5", "1.0", "1.5", "2.0", "3.0", "5.0"]
		current_speed = str(macro_data.get("speed", 1.0))
		self.speed_combo = wx.ComboBox(self, choices=self.speed_choices, style=wx.CB_DROPDOWN)
		self.speed_combo.SetValue(current_speed)
		self.speed_combo.SetName(
			_("Playback Speed. Choose a preset or type your own, like 1.3. 0 is instant."),
		)
		grid_sizer.Add(self.speed_combo, 1, wx.EXPAND)

		grid_sizer.Add(wx.StaticText(self, label=_("Start Delay (seconds):")), 0, wx.ALIGN_CENTER_VERTICAL)
		self.start_delay_choices = ["0", "0.25", "0.5", "1.0", "2.0", "3.0", "5.0", "10.0"]
		self.start_delay_combo = wx.ComboBox(
			self,
			choices=self.start_delay_choices,
			style=wx.CB_DROPDOWN,
		)
		self.start_delay_combo.SetValue(str(macro_data.get("start_delay", 0.0)))
		self.start_delay_combo.SetName(
			_(
				"Start Delay. This wait happens once before playback and is not affected by playback speed.",
			),
		)
		grid_sizer.Add(self.start_delay_combo, 1, wx.EXPAND)

		grid_sizer.Add(wx.StaticText(self, label=_("Security:")), 0, wx.ALIGN_CENTER_VERTICAL)
		self.lock_app = get_preferred_lock_app(macro_data)
		if self.lock_app:
			self.app_checkbox = wx.CheckBox(
				self,
				label=_("Run only in '{app_name}' application").format(app_name=self.lock_app),
			)
		else:
			self.app_checkbox = wx.CheckBox(self, label=_("Lock to current active application"))
		self.app_checkbox.SetName(_("Application Lock Security"))
		self.app_checkbox.SetValue(bool(macro_data.get("target_app")))
		grid_sizer.Add(self.app_checkbox, 1, wx.EXPAND)

		main_sizer.Add(grid_sizer, 0, wx.ALL | wx.EXPAND, 10)
		main_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 10)
		self.events_label = wx.StaticText(self, label=_("Macro Events (Keys and Delays):"))
		main_sizer.Add(self.events_label, 0, wx.LEFT | wx.RIGHT, 10)
		self.events_list = wx.ListBox(self, choices=self._build_event_strings(), style=wx.LB_EXTENDED)
		self.events_list.SetName(
			_("Macro Events List. You can use Shift and arrow keys for multiple selection."),
		)
		self.events_list.Bind(wx.EVT_LISTBOX, self.on_list_select)
		main_sizer.Add(self.events_list, 1, wx.ALL | wx.EXPAND, 10)

		event_btn_sizer = wx.GridSizer(3, 2, 5, 5)
		self.btn_edit_delay = wx.Button(self, label=_("Edit Delay"))
		self.btn_edit_delay.Bind(wx.EVT_BUTTON, self.on_edit_delay)
		event_btn_sizer.Add(self.btn_edit_delay, 0, wx.EXPAND)

		self.btn_edit_key = wx.Button(self, label=_("Edit Key"))
		self.btn_edit_key.Bind(wx.EVT_BUTTON, self.on_edit_key)
		event_btn_sizer.Add(self.btn_edit_key, 0, wx.EXPAND)

		self.btn_del_event = wx.Button(self, label=_("Delete Selected Event"))
		self.btn_del_event.Bind(wx.EVT_BUTTON, self.on_delete_event)
		event_btn_sizer.Add(self.btn_del_event, 0, wx.EXPAND)

		self.btn_move_up = wx.Button(self, label=_("Move Up"))
		self.btn_move_up.Bind(wx.EVT_BUTTON, self.on_move_up)
		event_btn_sizer.Add(self.btn_move_up, 0, wx.EXPAND)

		self.btn_move_down = wx.Button(self, label=_("Move Down"))
		self.btn_move_down.Bind(wx.EVT_BUTTON, self.on_move_down)
		event_btn_sizer.Add(self.btn_move_down, 0, wx.EXPAND)

		self.btn_add_event = wx.Button(self, label=_("Add Event"))
		self.btn_add_event.Bind(wx.EVT_BUTTON, self.on_add_event)
		event_btn_sizer.Add(self.btn_add_event, 0, wx.EXPAND)
		main_sizer.Add(event_btn_sizer, 0, wx.ALL | wx.EXPAND, 10)

		btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
		btn_ok = wx.Button(self, wx.ID_OK, label=_("Save"))
		btn_cancel = wx.Button(self, wx.ID_CANCEL, label=_("Cancel"))
		btn_sizer.Add(btn_ok, 0, wx.ALL, 5)
		btn_sizer.Add(btn_cancel, 0, wx.ALL, 5)
		main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER)

		self.SetSizer(main_sizer)
		self.Bind(wx.EVT_CHAR_HOOK, self.on_escape_press)

		del_id = wx.NewIdRef()
		up_id = wx.NewIdRef()
		down_id = wx.NewIdRef()
		undo_id = wx.NewIdRef()
		redo_id = wx.NewIdRef()
		copy_id = wx.NewIdRef()
		cut_id = wx.NewIdRef()
		paste_id = wx.NewIdRef()

		self.Bind(wx.EVT_MENU, self.on_delete_event, id=del_id)
		self.Bind(wx.EVT_MENU, self.on_move_up, id=up_id)
		self.Bind(wx.EVT_MENU, self.on_move_down, id=down_id)
		self.Bind(wx.EVT_MENU, self.on_undo, id=undo_id)
		self.Bind(wx.EVT_MENU, self.on_redo, id=redo_id)
		self.Bind(wx.EVT_MENU, self.on_copy, id=copy_id)
		self.Bind(wx.EVT_MENU, self.on_cut, id=cut_id)
		self.Bind(wx.EVT_MENU, self.on_paste, id=paste_id)

		accel_tbl = wx.AcceleratorTable(
			[
				(wx.ACCEL_NORMAL, wx.WXK_DELETE, del_id),
				(wx.ACCEL_CTRL, wx.WXK_UP, up_id),
				(wx.ACCEL_CTRL, wx.WXK_DOWN, down_id),
				(wx.ACCEL_CTRL, ord("Z"), undo_id),
				(wx.ACCEL_CTRL, ord("Y"), redo_id),
				(wx.ACCEL_CTRL, ord("C"), copy_id),
				(wx.ACCEL_CTRL, ord("X"), cut_id),
				(wx.ACCEL_CTRL, ord("V"), paste_id),
			],
		)
		self.SetAcceleratorTable(accel_tbl)
		wx.CallAfter(self.on_list_select, None)

	def on_copy(self, event):
		sels = self.events_list.GetSelections()
		if not sels:
			return
		self.clipboard_events = [copy.deepcopy(self.linear_events[i]) for i in sels]
		ui.message(_("{count} events copied.").format(count=len(self.clipboard_events)))

	def on_cut(self, event):
		sels = self.events_list.GetSelections()
		if not sels:
			return
		self.on_copy(None)
		self.on_delete_event(None)

	def on_paste(self, event):
		if not self.clipboard_events:
			return
		self.save_history()
		sels = list(self.events_list.GetSelections())
		insert_idx = max(sels) + 1 if sels else len(self.linear_events)

		for e in reversed(self.clipboard_events):
			self.linear_events.insert(insert_idx, copy.deepcopy(e))

		self.events_list.Set(self._build_event_strings())
		for i in range(self.events_list.GetCount()):
			self.events_list.Deselect(i)
		for i in range(len(self.clipboard_events)):
			self.events_list.Select(insert_idx + i)

		ui.message(_("{count} events pasted.").format(count=len(self.clipboard_events)))
		wx.CallAfter(self.on_list_select, None)
		self.events_list.SetFocus()

	def on_list_select(self, event):
		sels = self.events_list.GetSelections()
		if not sels:
			self.btn_edit_delay.Disable()
			self.btn_edit_key.Disable()
			self.btn_del_event.Disable()
			self.btn_move_up.Disable()
			self.btn_move_down.Disable()
			return

		self.btn_del_event.Enable()
		self.btn_move_up.Enable(0 not in sels)
		self.btn_move_down.Enable(len(self.linear_events) - 1 not in sels)

		has_delay = any(self.linear_events[s]["type"] == "delay" for s in sels)
		has_key = any(self.linear_events[s]["type"] != "delay" for s in sels)
		self.btn_edit_delay.Enable(has_delay and not has_key)
		self.btn_edit_key.Enable(has_key and not has_delay)

	def on_add_event(self, event):
		dlg = AddEventDialog(self)
		if dlg.ShowModal() == wx.ID_OK and dlg.new_event:
			self.save_history()
			sels = list(self.events_list.GetSelections())
			if sels:
				insert_idx = max(sels) + 1
			else:
				insert_idx = len(self.linear_events)

			self.linear_events.insert(insert_idx, dlg.new_event)
			self.events_list.Set(self._build_event_strings())

			for i in range(self.events_list.GetCount()):
				self.events_list.Deselect(i)
			self.events_list.SetSelection(insert_idx)
			ui.message(_("Event added."))
		dlg.Destroy()
		wx.CallAfter(self.on_list_select, None)
		self.events_list.SetFocus()

	def _linearize_events(self, events):
		linear = []
		i = 0
		modifiers = {16, 17, 18, 20, 91, 92, 160, 161, 162, 163, 164, 165}
		while i < len(events):
			e1 = events[i]
			if e1.get("delay", 0) > 0.001:
				linear.append({"type": "delay", "delay": e1["delay"]})
			if i + 1 < len(events) and e1["vkCode"] not in modifiers:
				e2 = events[i + 1]
				if e1["action"] == "keyDown" and e2["action"] == "keyUp" and e1["vkCode"] == e2["vkCode"]:
					linear.append(
						{
							"type": "press",
							"vkCode": e1["vkCode"],
							"scanCode": e1["scanCode"],
							"extended": e1.get("extended", False),
							"hold": e2.get("delay", 0.035),
						},
					)
					i += 2
					continue
			linear.append(
				{
					"type": e1["action"],
					"vkCode": e1["vkCode"],
					"scanCode": e1["scanCode"],
					"extended": e1.get("extended", False),
				},
			)
			i += 1
		return linear

	def _rebuild_events(self, linear):
		rebuilt = []
		current_delay = 0.0
		for e in linear:
			if e["type"] == "delay":
				current_delay += e["delay"]
			elif e["type"] == "press":
				rebuilt.append(
					{
						"action": "keyDown",
						"vkCode": e["vkCode"],
						"scanCode": e["scanCode"],
						"extended": e["extended"],
						"delay": current_delay,
					},
				)
				current_delay = e.get("hold", 0.035)
				rebuilt.append(
					{
						"action": "keyUp",
						"vkCode": e["vkCode"],
						"scanCode": e["scanCode"],
						"extended": e["extended"],
						"delay": current_delay,
					},
				)
				current_delay = 0.0
			else:
				rebuilt.append(
					{
						"action": e["type"],
						"vkCode": e["vkCode"],
						"scanCode": e["scanCode"],
						"extended": e["extended"],
						"delay": current_delay,
					},
				)
				current_delay = 0.0
		return rebuilt

	def save_history(self):
		self.undo_stack.append(copy.deepcopy(self.linear_events))
		self.redo_stack.clear()

	def on_undo(self, event):
		if self.undo_stack:
			self.redo_stack.append(copy.deepcopy(self.linear_events))
			self.linear_events = self.undo_stack.pop()
			self.events_list.Set(self._build_event_strings())
			ui.message(_("Undone."))

	def on_redo(self, event):
		if self.redo_stack:
			self.undo_stack.append(copy.deepcopy(self.linear_events))
			self.linear_events = self.redo_stack.pop()
			self.events_list.Set(self._build_event_strings())
			ui.message(_("Redone."))

	def on_escape_press(self, event):
		active_win = wx.Window.FindFocus()
		if event.GetKeyCode() == wx.WXK_ESCAPE:
			if active_win == self.events_list:
				for i in range(self.events_list.GetCount()):
					self.events_list.Deselect(i)
				self.on_list_select(None)
				ui.message(_("Selection cleared."))
			else:
				self.EndModal(wx.ID_CANCEL)
		elif event.GetKeyCode() == wx.WXK_SPACE and event.ControlDown():
			if active_win == self.events_list:
				idx = self.events_list.GetSelection()
				if idx != wx.NOT_FOUND:
					if self.events_list.IsSelected(idx):
						self.events_list.Deselect(idx)
					else:
						self.events_list.Select(idx)
					self.on_list_select(None)
		else:
			event.Skip()

	def _build_event_strings(self):
		str_list = []
		ui_idx = 1
		for e in self.linear_events:
			if e["type"] == "delay":
				str_list.append(f"{ui_idx}. {_('Wait')}: {int(e['delay'] * 1000)} ms")
			elif e["type"] == "press":
				key_name = get_key_name(e["vkCode"], e["scanCode"], e["extended"])
				hold_ms = int(e.get("hold", 0.035) * 1000)
				str_list.append(f"{ui_idx}. {_('Press')}: {key_name} ({_('hold')}: {hold_ms} ms)")
			elif e["type"] == "keyDown":
				key_name = get_key_name(e["vkCode"], e["scanCode"], e["extended"])
				str_list.append(f"{ui_idx}. {_('Key Down')}: {key_name}")
			elif e["type"] == "keyUp":
				key_name = get_key_name(e["vkCode"], e["scanCode"], e["extended"])
				str_list.append(f"{ui_idx}. {_('Key Up')}: {key_name}")
			ui_idx += 1
		return str_list

	def on_edit_key(self, event):
		sels = list(self.events_list.GetSelections())
		if sels:
			dlg = KeySelectDialog(self)
			if dlg.ShowModal() == wx.ID_OK and dlg.captured_vk:
				self.save_history()
				for s in sels:
					if self.linear_events[s]["type"] != "delay":
						self.linear_events[s]["vkCode"] = dlg.captured_vk
						self.linear_events[s]["scanCode"] = dlg.captured_scan
						self.linear_events[s]["extended"] = dlg.captured_ext
				self.events_list.Set(self._build_event_strings())
				for i in range(self.events_list.GetCount()):
					self.events_list.Deselect(i)
				for s in sels:
					self.events_list.SetSelection(s)
				ui.message(_("Key updated."))
			dlg.Destroy()
			wx.CallAfter(self.on_list_select, None)
			self.events_list.SetFocus()

	def on_edit_delay(self, event):
		sels = list(self.events_list.GetSelections())
		if sels:
			val_ms = 100
			if self.linear_events[sels[0]]["type"] == "delay":
				val_ms = int(self.linear_events[sels[0]]["delay"] * 1000)
			dlg = wx.TextEntryDialog(
				self,
				_("Enter the new wait time in milliseconds (ms):\n(Example: 1000 for 1 second)"),
				_("Edit Wait Time"),
				value=str(val_ms),
			)
			if dlg.ShowModal() == wx.ID_OK:
				val = dlg.GetValue().strip()
				if val.isdigit():
					self.save_history()
					new_delay_sec = int(val) / 1000.0
					for s in sels:
						if self.linear_events[s]["type"] == "delay":
							self.linear_events[s]["delay"] = new_delay_sec
					self.events_list.Set(self._build_event_strings())
					for i in range(self.events_list.GetCount()):
						self.events_list.Deselect(i)
					for s in sels:
						self.events_list.SetSelection(s)
					ui.message(_("Wait time updated."))
				else:
					ui.message(_("Error: Please enter numbers only."))
			dlg.Destroy()
			wx.CallAfter(self.on_list_select, None)
			self.events_list.SetFocus()

	def on_delete_event(self, event):
		sels = list(self.events_list.GetSelections())
		if sels:
			self.save_history()
			sels.sort(reverse=True)
			for s in sels:
				self.linear_events.pop(s)
			self.events_list.Set(self._build_event_strings())
			if self.events_list.GetCount() > 0:
				self.events_list.SetSelection(max(0, sels[-1] - 1))
			ui.message(_("Selected events deleted."))
			wx.CallAfter(self.on_list_select, None)
			self.events_list.SetFocus()

	def on_move_up(self, event):
		sels = list(self.events_list.GetSelections())
		if sels and sels[0] > 0:
			self.save_history()
			sels.sort()
			for s in sels:
				self.linear_events[s], self.linear_events[s - 1] = (
					self.linear_events[s - 1],
					self.linear_events[s],
				)
			self.events_list.Set(self._build_event_strings())
			for i in range(self.events_list.GetCount()):
				self.events_list.Deselect(i)
			for s in sels:
				self.events_list.SetSelection(s - 1)
			ui.message(_("Moved up."))
		self.events_list.SetFocus()

	def on_move_down(self, event):
		sels = list(self.events_list.GetSelections())
		if sels and sels[-1] < len(self.linear_events) - 1:
			self.save_history()
			sels.sort(reverse=True)
			for s in sels:
				self.linear_events[s], self.linear_events[s + 1] = (
					self.linear_events[s + 1],
					self.linear_events[s],
				)
			self.events_list.Set(self._build_event_strings())
			for i in range(self.events_list.GetCount()):
				self.events_list.Deselect(i)
			for s in sels:
				self.events_list.SetSelection(s + 1)
			ui.message(_("Moved down."))
		self.events_list.SetFocus()

	def on_infinite_toggle(self, event):
		self.loop_spin.Enable(not self.infinite_check.GetValue())

	def _parse_speed(self):
		raw_val = self.speed_combo.GetValue().strip()
		try:
			str_val = raw_val.split()[0].replace(",", ".")
			val = float(str_val)
			if val < 0:
				return 0.0
			return val
		except (IndexError, ValueError):
			return 1.0

	def _parse_start_delay(self):
		raw_val = self.start_delay_combo.GetValue().strip()
		try:
			str_val = raw_val.split()[0].replace(",", ".")
			val = float(str_val)
			if val < 0:
				return 0.0
			return val
		except (IndexError, ValueError):
			return 0.0

	def get_updated_data(self):
		final_target = resolve_target_application(self.app_checkbox.GetValue(), self.lock_app)
		loop_c = 0 if self.infinite_check.GetValue() else self.loop_spin.GetValue()
		return {
			"name": self.name_text.GetValue().strip() or _("Untitled Macro"),
			"loop_count": loop_c,
			"speed": self._parse_speed(),
			"start_delay": self._parse_start_delay(),
			"target_app": final_target,
			"events": self._rebuild_events(self.linear_events),
		}


class MacroManagerDialog(wx.Dialog):
	def __init__(self, parent, engine, storage, events_buffer, recorded_app, clear_buffer_callback):
		super(MacroManagerDialog, self).__init__(parent, title=_("Macro Manager"), size=(480, 680))
		self.engine = engine
		self.storage = storage
		self.events_buffer = events_buffer
		self.recorded_app = recorded_app
		self.clear_buffer_callback = clear_buffer_callback

		main_sizer = wx.BoxSizer(wx.VERTICAL)
		main_sizer.Add(wx.StaticText(self, label=_("Saved Macros:")), 0, wx.ALL, 5)
		choices = [m["name"] for m in self.storage.macros] if self.storage.macros else [_("No macros yet")]
		self.macro_list = wx.ListBox(self, choices=choices, style=wx.LB_EXTENDED)
		self.macro_list.SetName(_("Saved Macros List. Supports multiple selection."))
		main_sizer.Add(self.macro_list, 1, wx.ALL | wx.EXPAND, 5)

		list_btn_sizer = wx.GridSizer(1, 3, 5, 5)
		self.btn_play = wx.Button(self, label=_("Play"))
		self.btn_play.Bind(wx.EVT_BUTTON, self.on_play_click)
		list_btn_sizer.Add(self.btn_play, 0, wx.EXPAND)
		self.btn_edit = wx.Button(self, label=_("Edit"))
		self.btn_edit.Bind(wx.EVT_BUTTON, self.on_edit_click)
		list_btn_sizer.Add(self.btn_edit, 0, wx.EXPAND)
		self.btn_delete = wx.Button(self, label=_("Delete"))
		self.btn_delete.Bind(wx.EVT_BUTTON, self.on_delete_click)
		list_btn_sizer.Add(self.btn_delete, 0, wx.EXPAND)
		main_sizer.Add(list_btn_sizer, 0, wx.ALL | wx.EXPAND, 5)

		io_btn_sizer = wx.GridSizer(2, 2, 5, 5)
		self.btn_import = wx.Button(self, label=_("Import File"))
		self.btn_import.Bind(wx.EVT_BUTTON, self.on_import_click)
		io_btn_sizer.Add(self.btn_import, 0, wx.EXPAND)
		self.btn_export = wx.Button(self, label=_("Export File"))
		self.btn_export.Bind(wx.EVT_BUTTON, self.on_export_click)
		io_btn_sizer.Add(self.btn_export, 0, wx.EXPAND)
		self.btn_import_clip = wx.Button(self, label=_("Import from Clipboard"))
		self.btn_import_clip.Bind(wx.EVT_BUTTON, self.on_import_clip_click)
		io_btn_sizer.Add(self.btn_import_clip, 0, wx.EXPAND)
		self.btn_export_clip = wx.Button(self, label=_("Copy to Clipboard"))
		self.btn_export_clip.Bind(wx.EVT_BUTTON, self.on_export_clip_click)
		io_btn_sizer.Add(self.btn_export_clip, 0, wx.EXPAND)
		main_sizer.Add(io_btn_sizer, 0, wx.ALL | wx.EXPAND, 5)

		if self.events_buffer:
			main_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 10)
			main_sizer.Add(
				wx.StaticText(
					self,
					label=_("New Macro Process ({count} Events Captured):").format(
						count=len(self.events_buffer),
					),
				),
				0,
				wx.ALL,
				5,
			)
			grid_sizer = wx.FlexGridSizer(5, 2, 5, 5)
			grid_sizer.AddGrowableCol(1)
			grid_sizer.Add(wx.StaticText(self, label=_("Macro Name:")), 0, wx.ALIGN_CENTER_VERTICAL)
			self.name_text = wx.TextCtrl(self, value=_("New Macro"))
			self.name_text.SetName(_("Macro Name"))
			grid_sizer.Add(self.name_text, 1, wx.EXPAND)
			grid_sizer.Add(wx.StaticText(self, label=_("Loop Count:")), 0, wx.ALIGN_CENTER_VERTICAL)
			loop_box = wx.BoxSizer(wx.HORIZONTAL)
			self.loop_spin = wx.SpinCtrl(self, value="1", min=1, max=999)
			self.loop_spin.SetName(_("Loop Count"))
			loop_box.Add(self.loop_spin, 0, wx.RIGHT, 10)
			self.infinite_check = wx.CheckBox(self, label=_("Run until stopped"))
			self.infinite_check.SetName(_("Run until stopped (Infinite Loop)"))
			self.infinite_check.Bind(wx.EVT_CHECKBOX, self.on_infinite_toggle)
			loop_box.Add(self.infinite_check, 0, wx.ALIGN_CENTER_VERTICAL)
			grid_sizer.Add(loop_box, 1, wx.EXPAND)
			grid_sizer.Add(
				wx.StaticText(self, label=_("Playback Speed Multiplier (0 = Instant):")),
				0,
				wx.ALIGN_CENTER_VERTICAL,
			)
			self.speed_choices = ["0", "0.5", "1.0", "1.5", "2.0", "3.0", "5.0"]
			self.speed_combo = wx.ComboBox(self, choices=self.speed_choices, style=wx.CB_DROPDOWN)
			self.speed_combo.SetValue("1.0")
			self.speed_combo.SetName(
				_("Playback Speed. Choose a preset or type your own, like 1.3. 0 is instant."),
			)
			grid_sizer.Add(self.speed_combo, 1, wx.EXPAND)
			grid_sizer.Add(
				wx.StaticText(self, label=_("Start Delay (seconds):")),
				0,
				wx.ALIGN_CENTER_VERTICAL,
			)
			self.start_delay_choices = ["0", "0.25", "0.5", "1.0", "2.0", "3.0", "5.0", "10.0"]
			self.start_delay_combo = wx.ComboBox(
				self,
				choices=self.start_delay_choices,
				style=wx.CB_DROPDOWN,
			)
			self.start_delay_combo.SetValue("0")
			self.start_delay_combo.SetName(
				_(
					"Start Delay. This wait happens once before playback and is not affected by playback speed.",
				),
			)
			grid_sizer.Add(self.start_delay_combo, 1, wx.EXPAND)
			grid_sizer.Add(wx.StaticText(self, label=_("Security:")), 0, wx.ALIGN_CENTER_VERTICAL)
			app_label = (
				_("Run only in '{app_name}' application").format(app_name=self.recorded_app)
				if self.recorded_app
				else _("Lock to current active application")
			)
			self.app_checkbox = wx.CheckBox(self, label=app_label)
			self.app_checkbox.SetName(_("Application Lock Security"))
			grid_sizer.Add(self.app_checkbox, 1, wx.EXPAND)
			main_sizer.Add(grid_sizer, 0, wx.ALL | wx.EXPAND, 5)
			self.btn_save = wx.Button(self, label=_("Save Macro to Database"))
			self.btn_save.Bind(wx.EVT_BUTTON, self.on_save_click)
			main_sizer.Add(self.btn_save, 0, wx.ALL | wx.ALIGN_CENTER, 5)

		self.btn_close = wx.Button(self, wx.ID_CANCEL, label=_("Close"))
		self.btn_close.Bind(wx.EVT_BUTTON, self.on_close_click)
		main_sizer.Add(self.btn_close, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

		self.SetSizer(main_sizer)
		self.Bind(wx.EVT_CHAR_HOOK, self.on_escape_press)

		del_id = wx.NewIdRef()
		self.Bind(wx.EVT_MENU, self.on_delete_click, id=del_id)
		accel_tbl = wx.AcceleratorTable([(wx.ACCEL_NORMAL, wx.WXK_DELETE, del_id)])
		self.SetAcceleratorTable(accel_tbl)

		self.refresh_list()
		if self.storage.macros:
			self.macro_list.SetSelection(0)
			self.macro_list.SetFocus()

	def on_escape_press(self, event):
		if event.GetKeyCode() == wx.WXK_ESCAPE:
			self.on_close_click(None)
		else:
			event.Skip()

	def on_infinite_toggle(self, event):
		self.loop_spin.Enable(not self.infinite_check.GetValue())

	def on_play_click(self, event):
		sels = list(self.macro_list.GetSelections())
		if sels and self.storage.macros:
			macro = self.storage.macros[sels[0]]
			self.Destroy()
			self.engine.play_macro(
				macro["events"],
				macro.get("loop_count", 1),
				float(macro.get("speed", 1.0)),
				macro.get("target_app", None),
				float(macro.get("start_delay", 0.0)),
			)

	def on_edit_click(self, event):
		sels = list(self.macro_list.GetSelections())
		if sels and self.storage.macros:
			macro = self.storage.macros[sels[0]]
			dlg = MacroEditDialog(self, macro)
			if dlg.ShowModal() == wx.ID_OK:
				try:
					self.storage.update_macro(sels[0], dlg.get_updated_data())
					ui.message(_("Macro updated successfully."))
					self.refresh_list()
					self.macro_list.SetSelection(sels[0])
				except (MacroValidationError, MacroStorageError) as error:
					logHandler.log.error(f"NVDAMacroManager: Failed to update macro: {error}")
					ui.message(_("Could not update the macro. See the NVDA log for details."))
			dlg.Destroy()
			self.macro_list.SetFocus()

	def on_delete_click(self, event):
		sels = list(self.macro_list.GetSelections())
		if sels and self.storage.macros:
			sels.sort(reverse=True)
			try:
				deleted_names = self.storage.delete_macros(sels)
			except MacroStorageError as error:
				logHandler.log.error(f"NVDAMacroManager: Failed to delete macro: {error}")
				ui.message(_("Could not delete the selected macros. See the NVDA log for details."))
				return
			if len(deleted_names) == 1:
				ui.message(_("Macro '{name}' deleted.").format(name=deleted_names[0]))
			else:
				ui.message(_("{count} macros deleted.").format(count=len(deleted_names)))
			self.refresh_list()
			if self.storage.macros:
				self.macro_list.SetSelection(max(0, sels[-1] - 1))
			self.macro_list.SetFocus()

	def on_export_click(self, event):
		sels = list(self.macro_list.GetSelections())
		if sels and self.storage.macros:
			macro = self.storage.macros[sels[0]]
			with wx.FileDialog(
				self,
				_("Export Macro"),
				wildcard="JSON files (*.json)|*.json",
				defaultFile=f"{macro['name']}.json".replace(" ", "_"),
				style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
			) as fileDialog:
				if fileDialog.ShowModal() == wx.ID_CANCEL:
					return
				try:
					with open(fileDialog.GetPath(), "w", encoding="utf-8") as f:
						json.dump(macro, f, ensure_ascii=False, indent=4)
					ui.message(_("Macro '{name}' exported successfully.").format(name=macro["name"]))
				except (OSError, TypeError) as error:
					logHandler.log.error(f"NVDAMacroManager: Export failed: {error}")
					ui.message(_("Export failed."))
			self.macro_list.SetFocus()

	def on_import_click(self, event):
		with wx.FileDialog(
			self,
			_("Import Macro"),
			wildcard="JSON files (*.json)|*.json",
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
		) as fileDialog:
			if fileDialog.ShowModal() == wx.ID_CANCEL:
				return
			try:
				if os.path.getsize(fileDialog.GetPath()) > MAX_DECOMPRESSED_MACRO_BYTES:
					raise MacroValidationError("Macro file is too large")
				with open(fileDialog.GetPath(), "r", encoding="utf-8") as f:
					self.storage.import_macro(json.load(f))
				self.refresh_list()
				ui.message(_("Macro imported successfully."))
				self.macro_list.SetSelection(len(self.storage.macros) - 1)
			except (
				OSError,
				UnicodeError,
				json.JSONDecodeError,
				MacroValidationError,
				MacroStorageError,
			) as error:
				logHandler.log.error(f"NVDAMacroManager: Import failed: {error}")
				ui.message(_("Import failed."))
		self.macro_list.SetFocus()

	def on_export_clip_click(self, event):
		sels = self.macro_list.GetSelections()
		if sels and self.storage.macros:
			if self.storage.export_macro_to_clipboard(sels[0]):
				ui.message(
					_("Macro '{name}' copied to clipboard.").format(
						name=self.storage.macros[sels[0]]["name"],
					),
				)
			else:
				ui.message(_("Failed to copy macro to clipboard."))
		self.macro_list.SetFocus()

	def on_import_clip_click(self, event):
		success, msg = self.storage.import_macro_from_clipboard()
		if success:
			self.refresh_list()
			ui.message(_("Imported macro: {name}").format(name=msg))
			self.macro_list.SetSelection(len(self.storage.macros) - 1)
		else:
			ui.message(msg)
		self.macro_list.SetFocus()

	def _parse_speed(self):
		try:
			val = float(self.speed_combo.GetValue().strip().split()[0].replace(",", "."))
			return val if val >= 0 else 0.0
		except (IndexError, ValueError):
			return 1.0

	def _parse_start_delay(self):
		try:
			val = float(self.start_delay_combo.GetValue().strip().split()[0].replace(",", "."))
			return val if val >= 0 else 0.0
		except (IndexError, ValueError):
			return 0.0

	def on_save_click(self, event):
		name = self.name_text.GetValue().strip() or _("Untitled Macro")
		try:
			final_target = resolve_target_application(self.app_checkbox.GetValue(), self.recorded_app)
			self.storage.save_macro(
				name,
				0 if self.infinite_check.GetValue() else self.loop_spin.GetValue(),
				self._parse_speed(),
				final_target,
				self.recorded_app,
				self.events_buffer,
				self._parse_start_delay(),
			)
		except (MacroValidationError, MacroStorageError) as error:
			logHandler.log.error(f"NVDAMacroManager: Failed to save macro: {error}")
			ui.message(_("Could not save the macro. See the NVDA log for details."))
			return
		ui.message(_("Macro '{name}' saved successfully.").format(name=name))
		self.clear_buffer_callback()
		self.refresh_list()
		self.Destroy()

	def refresh_list(self):
		self.macro_list.Clear()
		if not self.storage.macros:
			self.macro_list.Append(_("No macros yet"))
			for btn in [self.btn_play, self.btn_edit, self.btn_delete, self.btn_export, self.btn_export_clip]:
				btn.Disable()
		else:
			for m in self.storage.macros:
				self.macro_list.Append(m["name"])
			for btn in [self.btn_play, self.btn_edit, self.btn_delete, self.btn_export, self.btn_export_clip]:
				btn.Enable()
			self.macro_list.SetSelection(0)
			self.macro_list.SetFocus()

	def on_close_click(self, event):
		self.Destroy()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super(GlobalPlugin, self).__init__()
		self.engine = MacroEngine(safe_stop_callback=self._stop_recording_and_notify)
		self.storage = MacroStorage(update_scripts_callback=self.inject_dynamic_scripts)
		self.gui_instance = None
		self.last_recorded_events = []
		self.last_recorded_app = None
		self.inject_dynamic_scripts()

	def inject_dynamic_scripts(self):
		cls = self.__class__
		for attr in list(dir(cls)):
			if attr.startswith("script_dynmacro_"):
				delattr(cls, attr)

		for m in self.storage.macros:
			macro_id = m["id"]
			safe_id = re.sub(r"[^0-9A-Za-z_]", "_", str(macro_id))
			func_name = f"script_dynmacro_{safe_id}"

			def make_script(current_macro_id, fname):
				def _script_func(self_inst, gesture):
					if self_inst.engine.is_playing:
						self_inst.engine.stop_playback_event.set()
						return
					macro_data = next(
						(macro for macro in self_inst.storage.macros if macro["id"] == current_macro_id),
						None,
					)
					if macro_data is None:
						logHandler.log.error(
							f"NVDAMacroManager: Dynamic script could not find macro {current_macro_id}",
						)
						return
					ui.message(_("Playing: {name}").format(name=macro_data["name"]))
					self_inst.engine.play_macro(
						macro_data["events"],
						macro_data.get("loop_count", 1),
						float(macro_data.get("speed", 1.0)),
						macro_data.get("target_app", None),
						float(macro_data.get("start_delay", 0.0)),
					)

				_script_func.__name__ = fname
				_script_func.__qualname__ = f"GlobalPlugin.{fname}"
				return _script_func

			decorated_script = scriptHandler.script(
				description=_("Custom Macro: {name}").format(name=m["name"]),
				category=_("Macro Manager"),
			)(make_script(macro_id, func_name))
			setattr(cls, func_name, decorated_script)

	def clear_buffer(self):
		self.last_recorded_events = []
		self.last_recorded_app = None

	@scriptHandler.script(
		description=_("Starts or stops live macro recording. (Keys are processed by the system)"),
		category=_("Macro Manager"),
		gesture="kb:nvda+windows+r",
	)
	def script_toggleMacroRecordingLive(self, gesture):
		if not self.engine.is_recording:
			if self.engine.start_recording(safe_mode=False):
				ui.message(_("Live macro recording started."))
			else:
				ui.message(_("Could not start macro recording. See the NVDA log for details."))
		else:
			self._stop_recording_and_notify()

	@scriptHandler.script(
		description=_("Starts safe macro recording. (Keys are hidden from the system)"),
		category=_("Macro Manager"),
		gesture="kb:nvda+windows+shift+r",
	)
	def script_toggleMacroRecordingSafe(self, gesture):
		if not self.engine.is_recording:
			if self.engine.start_recording(safe_mode=True):
				ui.message(_("Safe macro recording started. Keys are hidden."))
			else:
				ui.message(_("Could not start macro recording. See the NVDA log for details."))
		else:
			self._stop_recording_and_notify()

	def _stop_recording_and_notify(self):
		if not self.engine.is_recording:
			return
		self.last_recorded_events, self.last_recorded_app = self.engine.stop_recording()
		ui.message(
			_("Recording stopped. {count} events captured.").format(count=len(self.last_recorded_events)),
		)

	@scriptHandler.script(
		description=_("Plays the last recorded (temporary) macro. Cancels if currently playing."),
		category=_("Macro Manager"),
		gesture="kb:nvda+windows+p",
	)
	def script_playLastMacro(self, gesture):
		if self.engine.is_playing:
			self.engine.stop_playback_event.set()
		elif not self.last_recorded_events:
			ui.message(_("No temporary macro to play."))
		elif self.engine.is_recording:
			ui.message(_("Please stop recording first."))
		else:
			ui.message(_("Playing temporary macro..."))
			self.engine.play_macro(self.last_recorded_events, 1, 1.0, None)

	@scriptHandler.script(
		description=_("Opens the Macro Manager interface."),
		category=_("Macro Manager"),
		gesture="kb:nvda+shift+m",
	)
	def script_openMacroInterface(self, gesture):
		if self.engine.is_recording:
			self._stop_recording_and_notify()
		if self.gui_instance:
			try:
				if self.gui_instance.IsShown():
					self.gui_instance.Raise()
					self.gui_instance.SetFocus()
					return
			except RuntimeError:
				self.gui_instance = None
		gui.mainFrame.prePopup()
		self.gui_instance = MacroManagerDialog(
			gui.mainFrame,
			self.engine,
			self.storage,
			self.last_recorded_events,
			self.last_recorded_app,
			self.clear_buffer,
		)
		self.gui_instance.Bind(wx.EVT_WINDOW_DESTROY, self._on_manager_destroyed)
		self.gui_instance.Show()
		gui.mainFrame.postPopup()

	def _on_manager_destroyed(self, event):
		if event.GetEventObject() is self.gui_instance:
			self.gui_instance = None
		event.Skip()

	def terminate(self):
		self.engine.shutdown()
		if self.gui_instance:
			try:
				self.gui_instance.Destroy()
			except RuntimeError:
				pass
			self.gui_instance = None
		super().terminate()
