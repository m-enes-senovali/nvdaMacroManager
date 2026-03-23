import globalPluginHandler
import scriptHandler
import ui
import logHandler
import wx
import gui
import time
import ctypes
from ctypes import wintypes
import threading
import os
import json
import globalVars
import winUser
import appModuleHandler
import addonHandler
import copy
import core 

addonHandler.initTranslation()

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.windll.user32

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, ctypes.POINTER(KBDLLHOOKSTRUCT))
PUL = ctypes.POINTER(ctypes.c_ulong)

class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_ushort),
                ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]

def get_foreground_app():
    try:
        hwnd = winUser.getForegroundWindow()
        if not hwnd: return None
        threadID, processID = winUser.getWindowThreadProcessID(hwnd)
        return appModuleHandler.getAppNameFromProcessID(processID)
    except:
        return None

def get_key_name(vk, scan, ext):
    lparam = (scan << 16)
    if ext: lparam |= (1 << 24)
    buf = ctypes.create_unicode_buffer(64)
    if user32.GetKeyNameTextW(lparam, buf, 64): return buf.value
    return f"VK_{vk}"

def apply_dark_theme(window):
    bg_color = wx.Colour(40, 40, 40)
    fg_color = wx.Colour(220, 220, 220)
    window.SetBackgroundColour(bg_color)
    window.SetForegroundColour(fg_color)
    for child in window.GetChildren():
        if not isinstance(child, (wx.CheckBox, wx.Button, wx.SpinCtrl)):
            child.SetBackgroundColour(bg_color)
            child.SetForegroundColour(fg_color)

class MacroStorage:
    def __init__(self, update_scripts_callback=None):
        self.file_path = os.path.join(globalVars.appArgs.configPath, "nvda_macros.json")
        self.update_scripts_callback = update_scripts_callback
        self.macros = self.load_macros()

    def load_macros(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logHandler.log.error(f"NVDAMacroManager: Macro loading error: {e}")
        return []

    def save_macro(self, name, loop_count, speed, target_app, recorded_app, events):
        new_macro = {
            "id": str(time.time()), "name": name, "loop_count": loop_count,
            "speed": speed, "target_app": target_app, "recorded_app": recorded_app, "events": events
        }
        self.macros.append(new_macro)
        self._write_to_file()
        if self.update_scripts_callback: self.update_scripts_callback()

    def update_macro(self, index, updated_data):
        if 0 <= index < len(self.macros):
            self.macros[index].update(updated_data)
            self._write_to_file()
            if self.update_scripts_callback: self.update_scripts_callback()

    def delete_macro(self, index):
        if 0 <= index < len(self.macros):
            deleted_name = self.macros[index]["name"]
            self.macros.pop(index)
            self._write_to_file()
            if self.update_scripts_callback: self.update_scripts_callback()
            return deleted_name
        return None

    def import_macro(self, imported_data):
        if "name" in imported_data and "events" in imported_data:
            imported_data["id"] = str(time.time())
            self.macros.append(imported_data)
            self._write_to_file()
            if self.update_scripts_callback: self.update_scripts_callback()
            return True
        return False

    def _write_to_file(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.macros, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logHandler.log.error(f"NVDAMacroManager: Macro saving error: {e}")

class MacroEngine:
    def __init__(self):
        self.is_recording = False
        self.is_playing = False
        self.safe_mode = False 
        self.events = []
        self.last_time = 0.0
        self.hook_id = None
        self._hook_proc = HOOKPROC(self.low_level_keyboard_handler)
        self.recorded_app = None 
        self.stop_playback_event = threading.Event()
        
    def start_recording(self, safe_mode=False):
        self.events = []
        self.is_recording = True
        self.safe_mode = safe_mode
        self.last_time = time.perf_counter()
        self.hook_id = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._hook_proc, None, 0)
            
    def stop_recording(self):
        self.is_recording = False
        if self.hook_id:
            user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None
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
                    if trigger_vk is None: trigger_vk = vk 
                    elif trigger_vk != vk: break
                cut_index = i
                if e["delay"] > 0.5: break
            self.events = self.events[:cut_index]

        pressed_keys = {}
        for e in self.events:
            if e["action"] == "keyDown": pressed_keys[e["vkCode"]] = e
            elif e["action"] == "keyUp" and e["vkCode"] in pressed_keys: del pressed_keys[e["vkCode"]]
                
        for vk, e in pressed_keys.items():
            self.events.append({
                "action": "keyUp", "vkCode": vk, "scanCode": e["scanCode"],
                "extended": e["extended"], "delay": 0.05
            })
        return self.events, self.recorded_app

    def low_level_keyboard_handler(self, nCode, wParam, lParam):
        if nCode >= 0 and self.is_recording:
            injected = (lParam.contents.flags & 0x10) != 0
            if not injected:
                current_time = time.perf_counter()
                delay = current_time - self.last_time
                action = "unknown"
                if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN): action = "keyDown"
                elif wParam in (WM_KEYUP, WM_SYSKEYUP): action = "keyUp"
                vk = lParam.contents.vkCode
                self.events.append({
                    "action": action, "vkCode": vk, "scanCode": lParam.contents.scanCode,
                    "extended": (lParam.contents.flags & 0x01) != 0, "delay": delay
                })
                self.last_time = current_time
                
                if self.safe_mode:
                    nvda_down = any(user32.GetAsyncKeyState(k) & 0x8000 for k in (45, 96, 20))
                    shift_down = 1 if (user32.GetAsyncKeyState(16) & 0x8000) else 0
                    ctrl_down = 1 if (user32.GetAsyncKeyState(17) & 0x8000) else 0
                    alt_down = 1 if (user32.GetAsyncKeyState(18) & 0x8000) else 0
                    win_down = 1 if (user32.GetAsyncKeyState(91) & 0x8000) or (user32.GetAsyncKeyState(92) & 0x8000) else 0
                    major_mods_pressed = shift_down + ctrl_down + alt_down + win_down
                    modifiers = {16, 17, 18, 20, 45, 91, 92, 96, 160, 161, 162, 163, 164, 165}
                    
                    if not nvda_down and major_mods_pressed < 2 and vk not in modifiers:
                        return 1 
        return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

    def force_release_modifiers(self):
        modifiers = [16, 17, 18, 20, 91, 92, 160, 161, 162, 163, 164, 165]
        for m_vk in modifiers:
            if user32.GetAsyncKeyState(m_vk) & 0x8000:
                inp = Input()
                inp.type = INPUT_KEYBOARD
                inp.ii.ki.wVk = m_vk
                inp.ii.ki.wScan = 0
                inp.ii.ki.dwFlags = KEYEVENTF_KEYUP
                user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(Input))

    def play_macro(self, events_to_play, loop_count=1, speed=1.0, target_app=None):
        if not events_to_play or self.is_playing: return
            
        def playback_thread():
            self.is_playing = True
            self.stop_playback_event.clear()
            for _ in range(40): 
                current_app = get_foreground_app()
                if current_app and current_app.lower() != "nvda": break
                time.sleep(0.05)
            
            if target_app:
                current_app = get_foreground_app()
                if current_app and current_app.lower() != target_app.lower():
                    core.requestCorePump(lambda: ui.message(_("Security Warning: Macro locked to '{target_app}'. Current: '{current_app}'.").format(target_app=target_app, current_app=current_app)))
                    self.is_playing = False
                    return

            self.force_release_modifiers()
            loop_idx = 0
            while True:
                if self.stop_playback_event.is_set() or (loop_count != 0 and loop_idx >= loop_count): break
                for event in events_to_play:
                    if self.stop_playback_event.is_set(): break
                    actual_delay = event["delay"]
                    if speed <= 0: actual_delay = 0.005
                    else: actual_delay = actual_delay / speed
                    if event["action"] == "keyUp" and actual_delay < 0.035: actual_delay = 0.035
                    if actual_delay > 0: self.stop_playback_event.wait(actual_delay)
                    if self.stop_playback_event.is_set(): break

                    inp = Input()
                    inp.type = INPUT_KEYBOARD
                    inp.ii.ki.wVk = event["vkCode"] 
                    inp.ii.ki.wScan = event["scanCode"]
                    flags = 0
                    if event.get("extended", False): flags |= KEYEVENTF_EXTENDEDKEY
                    if event["action"] == "keyUp": flags |= KEYEVENTF_KEYUP
                    inp.ii.ki.dwFlags = flags
                    inp.ii.ki.time = 0
                    inp.ii.ki.dwExtraInfo = ctypes.cast(0, PUL)
                    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(Input))
                
                if not self.stop_playback_event.is_set(): self.stop_playback_event.wait(0.1)
                loop_idx += 1
                
            self.is_playing = False
            self.force_release_modifiers()
            
            if self.stop_playback_event.is_set(): 
                core.requestCorePump(lambda: ui.message(_("Macro playback canceled.")))
            else: 
                core.requestCorePump(lambda: ui.message(_("Macro playback completed.")))

        thread = threading.Thread(target=playback_thread)
        thread.daemon = True
        thread.start()


class MacroEditDialog(wx.Dialog):
    def __init__(self, parent, macro_data):
        super(MacroEditDialog, self).__init__(parent, title=_("Edit Macro (IDE)"), size=(600, 650))
        self.macro_data = macro_data
        self.events_copy = copy.deepcopy(macro_data.get("events", []))
        self.ui_to_events = [] 
        
        self.undo_stack = []
        self.redo_stack = []
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        grid_sizer = wx.FlexGridSizer(4, 2, 5, 5)
        
        grid_sizer.Add(wx.StaticText(self, label=_("Macro Name:")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.name_text = wx.TextCtrl(self, value=macro_data["name"])
        self.name_text.SetName(_("Macro Name"))
        grid_sizer.Add(self.name_text, 1, wx.EXPAND)
        
        grid_sizer.Add(wx.StaticText(self, label=_("Loop:")), 0, wx.ALIGN_CENTER_VERTICAL)
        loop_box = wx.BoxSizer(wx.HORIZONTAL)
        is_infinite = (macro_data.get("loop_count", 1) == 0)
        self.loop_spin = wx.SpinCtrl(self, value=str(macro_data.get("loop_count", 1) if not is_infinite else 1), min=1, max=999)
        self.loop_spin.SetName(_("Loop Count"))
        self.loop_spin.Enable(not is_infinite)
        loop_box.Add(self.loop_spin, 0, wx.RIGHT, 10)
        self.infinite_check = wx.CheckBox(self, label=_("Run until stopped"))
        self.infinite_check.SetName(_("Run until stopped (Infinite Loop)"))
        self.infinite_check.SetValue(is_infinite)
        self.infinite_check.Bind(wx.EVT_CHECKBOX, self.on_infinite_toggle)
        loop_box.Add(self.infinite_check, 0, wx.ALIGN_CENTER_VERTICAL)
        grid_sizer.Add(loop_box, 1, wx.EXPAND)
        
        grid_sizer.Add(wx.StaticText(self, label=_("Playback Speed Multiplier (0 = Instant):")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.speed_choices = ["0", "0.5", "1.0", "1.5", "2.0", "3.0", "5.0"]
        current_speed = str(macro_data.get("speed", 1.0))
        self.speed_combo = wx.ComboBox(self, choices=self.speed_choices, style=wx.CB_DROPDOWN)
        self.speed_combo.SetValue(current_speed)
        self.speed_combo.SetName(_("Playback Speed. Choose a preset or type your own, like 1.3. 0 is instant."))
        grid_sizer.Add(self.speed_combo, 1, wx.EXPAND)
        
        grid_sizer.Add(wx.StaticText(self, label=_("Security:")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.rec_app = macro_data.get("recorded_app", macro_data.get("target_app"))
        if self.rec_app: self.app_checkbox = wx.CheckBox(self, label=_("Run only in '{app_name}' application").format(app_name=self.rec_app))
        else: self.app_checkbox = wx.CheckBox(self, label=_("Lock to current active application"))
        self.app_checkbox.SetName(_("Application Lock Security"))
        self.app_checkbox.SetValue(bool(macro_data.get("target_app")))
        grid_sizer.Add(self.app_checkbox, 1, wx.EXPAND)
        
        main_sizer.Add(grid_sizer, 0, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 10)
        self.events_label = wx.StaticText(self, label=_("Macro Events (Keys and Delays):"))
        main_sizer.Add(self.events_label, 0, wx.LEFT | wx.RIGHT, 10)
        self.events_list = wx.ListBox(self, choices=self._build_event_strings(), style=wx.LB_EXTENDED)
        self.events_list.SetName(_("Macro Events List. You can use Shift and arrow keys for multiple selection."))
        main_sizer.Add(self.events_list, 1, wx.ALL | wx.EXPAND, 10)
        
        event_btn_sizer = wx.GridSizer(2, 2, 5, 5)
        self.btn_edit_delay = wx.Button(self, label=_("Edit Delay"))
        self.btn_edit_delay.Bind(wx.EVT_BUTTON, self.on_edit_delay)
        event_btn_sizer.Add(self.btn_edit_delay, 0, wx.EXPAND)
        self.btn_del_event = wx.Button(self, label=_("Delete Selected Event"))
        self.btn_del_event.Bind(wx.EVT_BUTTON, self.on_delete_event)
        event_btn_sizer.Add(self.btn_del_event, 0, wx.EXPAND)
        self.btn_move_up = wx.Button(self, label=_("Move Up"))
        self.btn_move_up.Bind(wx.EVT_BUTTON, self.on_move_up)
        event_btn_sizer.Add(self.btn_move_up, 0, wx.EXPAND)
        self.btn_move_down = wx.Button(self, label=_("Move Down"))
        self.btn_move_down.Bind(wx.EVT_BUTTON, self.on_move_down)
        event_btn_sizer.Add(self.btn_move_down, 0, wx.EXPAND)
        main_sizer.Add(event_btn_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_ok = wx.Button(self, wx.ID_OK, label=_("Save"))
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label=_("Cancel"))
        btn_sizer.Add(btn_ok, 0, wx.ALL, 5)
        btn_sizer.Add(btn_cancel, 0, wx.ALL, 5)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER)
        
        self.SetSizer(main_sizer)
        apply_dark_theme(self)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_escape_press)
        
        del_id = wx.NewIdRef()
        up_id = wx.NewIdRef()
        down_id = wx.NewIdRef()
        undo_id = wx.NewIdRef()
        redo_id = wx.NewIdRef()
        
        self.Bind(wx.EVT_MENU, self.on_delete_event, id=del_id)
        self.Bind(wx.EVT_MENU, self.on_move_up, id=up_id)
        self.Bind(wx.EVT_MENU, self.on_move_down, id=down_id)
        self.Bind(wx.EVT_MENU, self.on_undo, id=undo_id)
        self.Bind(wx.EVT_MENU, self.on_redo, id=redo_id)
        
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_NORMAL, wx.WXK_DELETE, del_id),
            (wx.ACCEL_CTRL, wx.WXK_UP, up_id),
            (wx.ACCEL_CTRL, wx.WXK_DOWN, down_id),
            (wx.ACCEL_CTRL, ord('Z'), undo_id),
            (wx.ACCEL_CTRL, ord('Y'), redo_id)
        ])
        self.SetAcceleratorTable(accel_tbl)

    def save_history(self):
        self.undo_stack.append(copy.deepcopy(self.events_copy))
        self.redo_stack.clear()

    def on_undo(self, event):
        if self.undo_stack:
            self.redo_stack.append(copy.deepcopy(self.events_copy))
            self.events_copy = self.undo_stack.pop()
            self.events_list.Set(self._build_event_strings())
            ui.message(_("Undone."))

    def on_redo(self, event):
        if self.redo_stack:
            self.undo_stack.append(copy.deepcopy(self.events_copy))
            self.events_copy = self.redo_stack.pop()
            self.events_list.Set(self._build_event_strings())
            ui.message(_("Redone."))

    def on_escape_press(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE: self.EndModal(wx.ID_CANCEL)
        else: event.Skip()

    def _build_event_strings(self):
        self.ui_to_events = []
        str_list = []
        i = 0
        ui_idx = 1
        while i < len(self.events_copy):
            e1 = self.events_copy[i]
            if i + 1 < len(self.events_copy):
                e2 = self.events_copy[i+1]
                if e1["action"] == "keyDown" and e2["action"] == "keyUp" and e1["vkCode"] == e2["vkCode"]:
                    self.ui_to_events.append([i, i+1])
                    key_name = get_key_name(e1["vkCode"], e1["scanCode"], e1.get("extended", False))
                    str_item = f"{ui_idx}. [{_('Press-Release')}] {key_name} - {_('Wait')}: {int(e1['delay'] * 1000)}ms, {_('Hold Time')}: {int(e2['delay'] * 1000)}ms"
                    str_list.append(str_item)
                    i += 2
                    ui_idx += 1
                    continue
            self.ui_to_events.append([i])
            key_name = get_key_name(e1["vkCode"], e1["scanCode"], e1.get("extended", False))
            action_str = _("Pressed") if e1["action"] == "keyDown" else _("Released")
            str_item = f"{ui_idx}. [{action_str}] {key_name} - {_('Wait')}: {int(e1['delay'] * 1000)}ms"
            str_list.append(str_item)
            i += 1
            ui_idx += 1
        return str_list

    def on_edit_delay(self, event):
        sels = list(self.events_list.GetSelections())
        if sels:
            first_event_idx = self.ui_to_events[sels[0]][0]
            current_delay_ms = int(self.events_copy[first_event_idx]["delay"] * 1000)
            dlg = wx.TextEntryDialog(self, _("Enter the new wait time in milliseconds (ms):\n(Example: 1000 for 1 second)"), _("Edit Wait Time"), value=str(current_delay_ms))
            if dlg.ShowModal() == wx.ID_OK:
                val = dlg.GetValue().strip()
                if val.isdigit():
                    self.save_history()
                    new_delay_sec = int(val) / 1000.0
                    for s in sels:
                        e_idx = self.ui_to_events[s][0]
                        self.events_copy[e_idx]["delay"] = new_delay_sec
                    self.events_list.Set(self._build_event_strings())
                    for i in range(self.events_list.GetCount()): self.events_list.Deselect(i)
                    for s in sels: self.events_list.SetSelection(s)
                    ui.message(_("Wait time updated."))
                else:
                    ui.message(_("Error: Please enter numbers only."))
            dlg.Destroy()
            self.events_list.SetFocus()

    def on_delete_event(self, event):
        sels = list(self.events_list.GetSelections())
        if sels:
            self.save_history()
            sels.sort(reverse=True)
            blocks = [[self.events_copy[idx] for idx in indices] for indices in self.ui_to_events]
            for s in sels: blocks.pop(s)
            self.events_copy = [e for b in blocks for e in b]
            self.events_list.Set(self._build_event_strings())
            if self.events_list.GetCount() > 0: self.events_list.SetSelection(max(0, sels[-1] - 1))
            ui.message(_("Selected events deleted."))
            self.events_list.SetFocus()

    def on_move_up(self, event):
        sels = list(self.events_list.GetSelections())
        if sels and sels[0] > 0:
            self.save_history()
            sels.sort()
            blocks = [[self.events_copy[idx] for idx in indices] for indices in self.ui_to_events]
            for s in sels: blocks[s], blocks[s-1] = blocks[s-1], blocks[s]
            self.events_copy = [e for b in blocks for e in b]
            self.events_list.Set(self._build_event_strings())
            for i in range(self.events_list.GetCount()): self.events_list.Deselect(i)
            for s in sels: self.events_list.SetSelection(s - 1)
            ui.message(_("Moved up."))
        self.events_list.SetFocus()

    def on_move_down(self, event):
        sels = list(self.events_list.GetSelections())
        if sels and sels[-1] < len(self.ui_to_events) - 1:
            self.save_history()
            sels.sort(reverse=True)
            blocks = [[self.events_copy[idx] for idx in indices] for indices in self.ui_to_events]
            for s in sels: blocks[s], blocks[s+1] = blocks[s+1], blocks[s]
            self.events_copy = [e for b in blocks for e in b]
            self.events_list.Set(self._build_event_strings())
            for i in range(self.events_list.GetCount()): self.events_list.Deselect(i)
            for s in sels: self.events_list.SetSelection(s + 1)
            ui.message(_("Moved down."))
        self.events_list.SetFocus()

    def on_infinite_toggle(self, event):
        self.loop_spin.Enable(not self.infinite_check.GetValue())
        
    def _parse_speed(self):
        raw_val = self.speed_combo.GetValue().strip()
        str_val = raw_val.split()[0].replace(',', '.') 
        try:
            val = float(str_val)
            if val < 0: return 0.0
            return val
        except ValueError: return 1.0

    def get_updated_data(self):
        target_app = self.rec_app
        if not target_app and self.app_checkbox.GetValue(): target_app = get_foreground_app()
        final_target = target_app if self.app_checkbox.GetValue() else None
        loop_c = 0 if self.infinite_check.GetValue() else self.loop_spin.GetValue()
        return {
            "name": self.name_text.GetValue().strip() or _("Untitled Macro"),
            "loop_count": loop_c, "speed": self._parse_speed(), 
            "target_app": final_target, "events": self.events_copy
        }


class MacroManagerDialog(wx.Dialog):
    def __init__(self, parent, engine, storage, events_buffer, recorded_app, clear_buffer_callback):
        super(MacroManagerDialog, self).__init__(parent, title=_("Macro Manager"), size=(480, 650))
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

        io_btn_sizer = wx.GridSizer(1, 2, 5, 5)
        self.btn_import = wx.Button(self, label=_("Import"))
        self.btn_import.Bind(wx.EVT_BUTTON, self.on_import_click)
        io_btn_sizer.Add(self.btn_import, 0, wx.EXPAND)
        self.btn_export = wx.Button(self, label=_("Export"))
        self.btn_export.Bind(wx.EVT_BUTTON, self.on_export_click)
        io_btn_sizer.Add(self.btn_export, 0, wx.EXPAND)
        main_sizer.Add(io_btn_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        if self.events_buffer:
            main_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 10)
            main_sizer.Add(wx.StaticText(self, label=_("New Macro Process ({count} Events Captured):").format(count=len(self.events_buffer))), 0, wx.ALL, 5)
            grid_sizer = wx.FlexGridSizer(4, 2, 5, 5)
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
            grid_sizer.Add(wx.StaticText(self, label=_("Playback Speed Multiplier (0 = Instant):")), 0, wx.ALIGN_CENTER_VERTICAL)
            self.speed_choices = ["0", "0.5", "1.0", "1.5", "2.0", "3.0", "5.0"]
            self.speed_combo = wx.ComboBox(self, choices=self.speed_choices, style=wx.CB_DROPDOWN)
            self.speed_combo.SetValue("1.0")
            self.speed_combo.SetName(_("Playback Speed. Choose a preset or type your own, like 1.3. 0 is instant."))
            grid_sizer.Add(self.speed_combo, 1, wx.EXPAND)
            grid_sizer.Add(wx.StaticText(self, label=_("Security:")), 0, wx.ALIGN_CENTER_VERTICAL)
            app_label = _("Run only in '{app_name}' application").format(app_name=self.recorded_app) if self.recorded_app else _("Lock to current active application")
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
        apply_dark_theme(self)
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
        if event.GetKeyCode() == wx.WXK_ESCAPE: self.on_close_click(None)
        else: event.Skip()

    def on_infinite_toggle(self, event):
        self.loop_spin.Enable(not self.infinite_check.GetValue())

    def on_play_click(self, event):
        sels = list(self.macro_list.GetSelections())
        if sels and self.storage.macros:
            macro = self.storage.macros[sels[0]]
            self.Destroy()
            self.engine.play_macro(macro["events"], macro.get("loop_count", 1), float(macro.get("speed", 1.0)), macro.get("target_app", None))

    def on_edit_click(self, event):
        sels = list(self.macro_list.GetSelections())
        if sels and self.storage.macros:
            macro = self.storage.macros[sels[0]]
            dlg = MacroEditDialog(self, macro)
            if dlg.ShowModal() == wx.ID_OK:
                self.storage.update_macro(sels[0], dlg.get_updated_data())
                ui.message(_("Macro updated successfully."))
                self.refresh_list()
                self.macro_list.SetSelection(sels[0])
            dlg.Destroy()
            self.macro_list.SetFocus()

    def on_delete_click(self, event):
        sels = list(self.macro_list.GetSelections())
        if sels and self.storage.macros:
            sels.sort(reverse=True)
            if len(sels) == 1:
                deleted_name = self.storage.macros[sels[0]]["name"]
                self.storage.delete_macro(sels[0])
                ui.message(_("Macro '{name}' deleted.").format(name=deleted_name))
            else:
                for s in sels: self.storage.delete_macro(s)
                ui.message(_("{count} macros deleted.").format(count=len(sels)))
            self.refresh_list()
            if self.storage.macros: self.macro_list.SetSelection(max(0, sels[-1] - 1))
            self.macro_list.SetFocus()

    def on_export_click(self, event):
        sels = list(self.macro_list.GetSelections())
        if sels and self.storage.macros:
            macro = self.storage.macros[sels[0]]
            with wx.FileDialog(self, _("Export Macro"), wildcard="JSON files (*.json)|*.json", defaultFile=f"{macro['name']}.json".replace(" ", "_"), style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
                if fileDialog.ShowModal() == wx.ID_CANCEL: return
                try:
                    with open(fileDialog.GetPath(), 'w', encoding='utf-8') as f: json.dump(macro, f, ensure_ascii=False, indent=4)
                    ui.message(_("Macro '{name}' exported successfully.").format(name=macro['name']))
                except Exception as e:
                    ui.message(_("Export failed."))
            self.macro_list.SetFocus()

    def on_import_click(self, event):
        with wx.FileDialog(self, _("Import Macro"), wildcard="JSON files (*.json)|*.json", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL: return
            try:
                with open(fileDialog.GetPath(), 'r', encoding='utf-8') as f:
                    if self.storage.import_macro(json.load(f)):
                        self.refresh_list()
                        ui.message(_("Macro imported successfully."))
                        self.macro_list.SetSelection(len(self.storage.macros) - 1)
                    else: ui.message(_("Invalid macro file."))
            except Exception as e:
                ui.message(_("Import failed."))
        self.macro_list.SetFocus()

    def _parse_speed(self):
        try:
            val = float(self.speed_combo.GetValue().strip().split()[0].replace(',', '.'))
            return val if val >= 0 else 0.0
        except ValueError: return 1.0

    def on_save_click(self, event):
        target_app = get_foreground_app() if (not self.recorded_app and self.app_checkbox.GetValue()) else self.recorded_app
        final_target = target_app if self.app_checkbox.GetValue() else None
        name = self.name_text.GetValue().strip() or _("Untitled Macro")
        self.storage.save_macro(name, 0 if self.infinite_check.GetValue() else self.loop_spin.GetValue(), self._parse_speed(), final_target, target_app, self.events_buffer)
        ui.message(_("Macro '{name}' saved successfully.").format(name=name))
        self.clear_buffer_callback()
        self.refresh_list()
        self.Destroy()

    def refresh_list(self):
        self.macro_list.Clear()
        if not self.storage.macros:
            self.macro_list.Append(_("No macros yet"))
            for btn in [self.btn_play, self.btn_edit, self.btn_delete, self.btn_export]: btn.Disable()
        else:
            for m in self.storage.macros: self.macro_list.Append(m["name"])
            for btn in [self.btn_play, self.btn_edit, self.btn_delete, self.btn_export]: btn.Enable()
            self.macro_list.SetSelection(0)
            self.macro_list.SetFocus()

    def on_close_click(self, event):
        self.Destroy()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    def __init__(self):
        super(GlobalPlugin, self).__init__()
        self.engine = MacroEngine()
        self.storage = MacroStorage(update_scripts_callback=self.inject_dynamic_scripts)
        self.gui_instance = None
        self.last_recorded_events = []
        self.last_recorded_app = None
        self.inject_dynamic_scripts()

    def inject_dynamic_scripts(self):
        cls = self.__class__
        for attr in list(dir(cls)):
            if attr.startswith("script_dynmacro_"): delattr(cls, attr)
                
        for m in self.storage.macros:
            safe_id = m['id'].replace('.', '_')
            func_name = f"script_dynmacro_{safe_id}"
            
            def make_script(macro_data, fname):
                def _script_func(self_inst, gesture):
                    if self_inst.engine.is_playing:
                        self_inst.engine.stop_playback_event.set()
                        return
                    ui.message(_("Playing: {name}").format(name=macro_data['name']))
                    self_inst.engine.play_macro(macro_data["events"], macro_data.get("loop_count", 1), float(macro_data.get("speed", 1.0)), macro_data.get("target_app", None))
                
                _script_func.__name__ = fname
                _script_func.__qualname__ = f"GlobalPlugin.{fname}"
                return _script_func
                
            decorated_script = scriptHandler.script(
                description=_("Custom Macro: {name}").format(name=m['name']),
                category=_("Macro Manager")
            )(make_script(m, func_name))
            setattr(cls, func_name, decorated_script)

    def clear_buffer(self):
        self.last_recorded_events = []
        self.last_recorded_app = None

    @scriptHandler.script(description=_("Starts or stops live macro recording. (Keys are processed by the system)"), category=_("Macro Manager"), gesture="kb:nvda+windows+r")
    def script_toggleMacroRecordingLive(self, gesture):
        if not self.engine.is_recording:
            self.engine.start_recording(safe_mode=False)
            ui.message(_("Live macro recording started."))
        else: self._stop_recording_and_notify()

    @scriptHandler.script(description=_("Starts safe macro recording. (Keys are hidden from the system)"), category=_("Macro Manager"), gesture="kb:nvda+windows+shift+r")
    def script_toggleMacroRecordingSafe(self, gesture):
        if not self.engine.is_recording:
            self.engine.start_recording(safe_mode=True)
            ui.message(_("Safe macro recording started. Keys are hidden."))
        else: self._stop_recording_and_notify()

    def _stop_recording_and_notify(self):
        self.last_recorded_events, self.last_recorded_app = self.engine.stop_recording()
        ui.message(_("Recording stopped. {count} events captured.").format(count=len(self.last_recorded_events)))

    @scriptHandler.script(description=_("Plays the last recorded (temporary) macro. Cancels if currently playing."), category=_("Macro Manager"), gesture="kb:nvda+windows+p")
    def script_playLastMacro(self, gesture):
        if self.engine.is_playing: self.engine.stop_playback_event.set()
        elif not self.last_recorded_events: ui.message(_("No temporary macro to play."))
        elif self.engine.is_recording: ui.message(_("Please stop recording first."))
        else:
            ui.message(_("Playing temporary macro..."))
            self.engine.play_macro(self.last_recorded_events, 1, 1.0, None)

    @scriptHandler.script(description=_("Opens the Macro Manager interface."), category=_("Macro Manager"), gesture="kb:nvda+shift+m")
    def script_openMacroInterface(self, gesture):
        if self.engine.is_recording: self._stop_recording_and_notify()
        gui.mainFrame.prePopup()
        self.gui_instance = MacroManagerDialog(gui.mainFrame, self.engine, self.storage, self.last_recorded_events, self.last_recorded_app, self.clear_buffer)
        self.gui_instance.Show()
        gui.mainFrame.postPopup()