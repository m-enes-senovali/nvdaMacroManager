# NVDAMacroManager (Modern Macro Manager)

**Developer:** Muhammet Enes Şenovalı
**Version:** 1.0.2

NVDA Macro Manager is an accessibility-centric, low-level OS-based, high-performance, and fully NVDA-integrated macro recording, editing, and playback engine. It flawlessly automates all your repetitive tasks, from gaming to daily office work.

## 🚀 Key Features

* **Dual Recording Engine (Live and Stealth Mode):** You can record your macros either by seeing the actions on screen (Live) or completely hidden from the system (Stealth Mode). In Stealth mode, keystrokes are intercepted and not sent to the OS, preventing accidental file deletions or window closures while recording.
* **Dynamic Shortcuts:** You can assign custom hotkeys to each saved macro directly from NVDA's `Preferences -> Input Gestures -> Macro Manager` menu. Trigger your macros in seconds without opening the interface.
* **Advanced Macro IDE (Event Editor):** * Recorded keys are smartly visually merged into "Press-Release" events for better readability.
  * **Multi-Select:** Use the `Shift` key to select multiple events and apply bulk delay times.
  * **Accelerators:** Instantly delete events with `Delete`, and move macro steps up or down using `Ctrl + Up/Down Arrow`.
  * **Undo/Redo:** Made a mistake while editing? Simply press `Ctrl + Z` to undo and `Ctrl + Y` to redo.
* **Game Compatible (Anti-Cheat Bypass):** Works seamlessly without triggering game security systems by sending hardware codes (ScanCodes).
* **Precision Speed & Loop Control:** Adjust playback speed in 0.1 increments (e.g., 1.3x), play instantly (0 delay), or set to an infinite loop.
* **Instant Kill Switch:** Stop an out-of-control macro instantly by pressing the playback shortcut again.
* **App-Binding (Security):** Lock your macros to run only in specific applications (.exe).

## ⌨️ Default Shortcuts

* **`NVDA + Windows + R`** : Starts or stops **LIVE** macro recording. (Your keystrokes are processed by the operating system).
* **`NVDA + Windows + Shift + R`** : Starts or stops **SAFE (STEALTH)** macro recording. (Keys pressed during recording are hidden from the system; nothing happens on your computer).
* **`NVDA + Windows + P`** : Plays the last recorded (temporary) macro. **If pressed while a macro is playing, it instantly cancels the operation.**
* **`NVDA + Shift + M`** : Opens the Macro Manager interface.

## 🛠️ How to Use?

### 1. Quick Macro Recording
* Use `NVDA + Win + R` if you want to see the actions happen on your screen.
* Use `NVDA + Win + Shift + R` if you are going to press dangerous keys (`Delete`, `Alt+F4`, etc.) and don't want your computer to be affected.
* Press the same shortcut again to stop recording. You can immediately test this temporary macro with `NVDA + Win + P`.

### 2. Saving Macros and Using the IDE
To save your temporary macro, open the manager with `NVDA + Shift + M`. Give your macro a name, set its speed or loop count, and click "Save".

Select a saved macro from the list and click **Edit** to open the IDE. Here:
* Use `Shift` to select multiple keys in the events list.
* Edit the wait times (in milliseconds) of the selected keys.
* Delete unwanted keystrokes with the `Delete` key.
* If you make a mistake, instantly revert it using `Ctrl + Z`.

### 3. Assigning Custom Shortcuts
After saving your macro, go to `Preferences -> Input Gestures` from the NVDA menu. Find the **Macro Manager** category. You will see the name of your saved macro there. Click "Add" and assign any key combination you desire.