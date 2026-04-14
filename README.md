# NVDAMacroManager (Modern Macro IDE & Automation Engine)

**Developer:** Muhammet Enes Şenovalı  
**Version:** 1.0.3  

NVDA Macro Manager is an accessibility-centric, low-level OS-based, high-performance macro recording, editing, and playback engine. It flawlessly automates your repetitive tasks, from complex gaming combos to daily office workflows, fully integrated into the NVDA screen reader.

## 🚀 Key Features

* **Dual Recording Engine (Live and Stealth Mode):** Record your macros either by seeing the actions on screen (Live) or completely hidden from the system (Stealth Mode). In Stealth mode, keystrokes are intercepted before reaching the OS, preventing accidental file deletions or window closures while recording.
* **Dynamic NVDA Shortcuts:** Automatically injects your saved macros into NVDA's system. You can assign custom hotkeys to each macro directly from NVDA's `Preferences -> Input Gestures -> Macro Manager` menu. Trigger your macros in seconds without opening the interface.
* **Professional Macro IDE (Event Editor):** Manage your macros like a pro developer.
  * **Linear Workflow:** Keys and delays are separated into clean, independent steps (Wait, Press, Key Down, Key Up).
  * **Native Clipboard:** Full support for `Ctrl + C`, `Ctrl + X`, and `Ctrl + V` to duplicate or move macro events seamlessly.
  * **Undo/Redo:** Made a mistake? Instantly revert it using `Ctrl + Z` (Undo) or `Ctrl + Y` (Redo).
  * **Dynamic Event Injection:** Forgot to press a key during recording? Add new delays or specific keystrokes anywhere in the macro without re-recording.
* **Intelligent Key Capture:** When adding or editing a key, capture actual physical keypresses or select from a dynamically generated, localized OS-level dropdown menu (Letters, Punctuation, Numpad, System keys).
* **Game & Anti-Cheat Compatible:** Works seamlessly without triggering game security systems by utilizing hardware-level execution (SendInput API and ScanCodes).
* **Precision Speed & Loop Control:** Adjust playback speed in 0.1 increments (e.g., 1.3x), play instantly (0 delay), or set to an infinite loop.
* **App-Binding (Security Locks):** Lock your macros to run only in specific applications (.exe) to prevent disastrous cross-app executions.
* **Multilingual (i18n):** Native support for English, Turkish (`tr`), Spanish (`es`), and German (`de`).

## ⌨️ Default Shortcuts

* **`NVDA + Windows + R`** : Starts or stops **LIVE** macro recording. (Your keystrokes are processed by the operating system).
* **`NVDA + Windows + Shift + R`** : Starts or stops **SAFE (STEALTH)** macro recording. (Keys pressed are completely hidden from the OS).
* **`NVDA + Windows + P`** : Plays the last recorded (temporary) macro. **If pressed while a macro is playing, it acts as an instant Kill Switch to cancel the operation.**
* **`NVDA + Shift + M`** : Opens the Macro Manager interface.

## 🛠️ How to Use?

### 1. Quick Macro Recording
* Press `NVDA + Win + R` to record normally.
* Use `NVDA + Win + Shift + R` if you are going to press system-altering keys (`Delete`, `Alt+F4`, etc.) and don't want your computer to act on them during recording.
* Press the same shortcut again to stop recording. Test your temporary macro immediately with `NVDA + Win + P`.

### 2. Saving Macros and Using the IDE
To save a temporary macro permanently, open the manager with `NVDA + Shift + M`. Give it a name, set its speed or loop count, and click "Save".

Select a saved macro from the list and click **Edit** to open the IDE:
* Use `Shift` to select multiple events.
* Press `Ctrl + C` to copy selected steps and `Ctrl + V` to paste them elsewhere.
* Change delay times in bulk or modify specific captured keystrokes.
* Add brand new events via the "Add Event" button.

### 3. Assigning Custom Shortcuts
After saving your macro, go to `Preferences -> Input Gestures` from the NVDA menu. Expand the **Macro Manager** category. Find your macro's name, click "Add," and assign any physical key combination you desire.
