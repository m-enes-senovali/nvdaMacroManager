# NVDAMacroManager (Modern Macro IDE & Automation Engine)

**Developer:** Muhammet Enes Şenovalı
**Version:** 1.2.4

NVDA Macro Manager is an accessibility-focused keyboard macro recorder, editor, and playback engine integrated with the NVDA screen reader. It is intended for repeatable desktop workflows where the target application and recorded key sequence are known.

## 🚀 Key Features

* **Dual Recording Engine (Live and Safe Mode):** Live mode lets keystrokes reach applications while they are recorded. Safe mode suppresses recorded physical keystrokes until you stop with `NVDA + Windows + Shift + R`.
* **Dynamic NVDA Shortcuts:** Automatically injects your saved macros into NVDA's system. You can assign custom hotkeys to each macro directly from NVDA's `Preferences -> Input Gestures -> Macro Manager` menu. Trigger your macros in seconds without opening the interface.
* **Professional Macro IDE (Event Editor):** Manage your macros like a pro developer.
  * **Linear Workflow:** Keys and delays are separated into clean, independent steps (Wait, Press, Key Down, Key Up).
  * **Native Clipboard:** Full support for `Ctrl + C`, `Ctrl + X`, and `Ctrl + V` to duplicate or move macro events seamlessly.
  * **Undo/Redo:** Made a mistake? Instantly revert it using `Ctrl + Z` (Undo) or `Ctrl + Y` (Redo).
  * **Dynamic Event Injection:** Forgot to press a key during recording? Add new delays or specific keystrokes anywhere in the macro without re-recording.
* **Intelligent Key Capture:** When adding or editing a key, capture actual physical keypresses or select from a dynamically generated, localized OS-level dropdown menu (Letters, Punctuation, Numpad, System keys).
* **Windows Input Playback:** Replays keyboard input with the Windows `SendInput` API. Some protected, elevated, remote, or game applications may reject simulated input; anti-cheat compatibility is not guaranteed.
* **Precision Speed, Start Delay & Loop Control:** Adjust playback speed in 0.1 increments (e.g., 1.3x), choose a speed-independent delay before the first event, play instantly, or set an infinite loop.
* **App-Binding (Security Locks):** Lock a macro to a specific application. Playback refuses to start if the application cannot be verified and stops if focus moves elsewhere.
* **Multilingual (i18n):** Complete interface catalogs for English, Turkish (`tr`), Spanish (`es`), German (`de`), and Portuguese (Portugal) (`pt_PT`).

## ⌨️ Default Shortcuts

* **`NVDA + Windows + R`** : Starts or stops **LIVE** macro recording. (Your keystrokes are processed by the operating system).
* **`NVDA + Windows + Shift + R`** : Starts or stops **SAFE** macro recording. Physical keystrokes are suppressed while recording; the stop shortcut remains available.
* **`NVDA + Windows + P`** : Plays the last recorded (temporary) macro. **If pressed while a macro is playing, it acts as an instant Kill Switch to cancel the operation.**
* **`NVDA + Shift + M`** : Opens the Macro Manager interface.

## 📦 Installation

1. Download the latest `.nvda-addon` file from [GitHub Releases](https://github.com/m-enes-senovali/nvdaMacroManager/releases).
2. Open the downloaded file while NVDA is running and confirm the installation prompt.
3. Restart NVDA when requested, then verify **NVDA menu → Tools → Add-on Store → Installed add-ons**.

NVDA 2023.1 or later is required. The add-on supports Windows only because recording and playback use Windows keyboard APIs.

## 🛠️ How to Use?

### 1. Quick Macro Recording
* Press `NVDA + Win + R` to record normally.
* Use `NVDA + Win + Shift + R` if you are going to press system-altering keys (`Delete`, `Alt+F4`, etc.) and don't want your computer to act on them during recording.
* Press the same shortcut again to stop recording. Test your temporary macro immediately with `NVDA + Win + P`.

### 2. Saving Macros and Using the IDE
To save a temporary macro permanently, open the manager with `NVDA + Shift + M`. Give it a name, set its speed, start delay, and loop count, then click "Save". Start delay is applied once before the first event and is not multiplied or divided by playback speed.

Select a saved macro from the list and click **Edit** to open the IDE:
* Use `Shift` to select multiple events.
* Press `Ctrl + C` to copy selected steps and `Ctrl + V` to paste them elsewhere.
* Change delay times in bulk or modify specific captured keystrokes.
* Add brand new events via the "Add Event" button.

### 3. Assigning Custom Shortcuts
After saving your macro, go to `Preferences -> Input Gestures` from the NVDA menu. Expand the **Macro Manager** category. Find your macro's name, click "Add," and assign any physical key combination you desire.

## 🔒 Data and Safety

Saved macros are stored as `nvda_macros.json` in the active NVDA configuration directory. Database updates are written atomically and the previous file is retained as `nvda_macros.json.bak`. Clipboard and file imports are validated and size-limited before use.

Safe recording suppresses physical keystrokes, but playback still performs real keyboard actions. Review imported macros, test them in a non-critical application first, and use application locks where possible. The add-on cannot bypass Windows integrity levels, protected applications, remote-session restrictions, or game security controls.

## 🧪 Development and Contributing

The repository follows the official NVDA AddonTemplate layout and uses Python 3.13. A typical local workflow is:

```powershell
uv sync
uv run pre-commit run --all-files
uv run python -m unittest discover -s tests -v
uv run scons
uv run scons pot
```

GNU gettext is optional for local builds; the build falls back to `polib` for PO/MO/POT operations. Before opening a pull request, run the checks above and describe the tested NVDA/Windows versions and any behavior that could not be verified. Bug reports should include reproduction steps, expected and actual behavior, the NVDA version, Windows version, and relevant NVDA log excerpts without private data.
