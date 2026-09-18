# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.8] - 2026-09-18

### Fixed
- Foreground-application identification now uses the process ID returned by NVDA's window helper instead of mistakenly using the thread ID.
- Application-locked playback now identifies applications such as Audacity and Sound Forge correctly while retaining the existing fail-closed security checks.

## [1.2.7] - 2026-09-17

### Fixed
- Application-locked playback started from Macro Manager now waits through the brief interval in which Windows may report no foreground application while the manager closes.
- The security check still fails closed if no verifiable non-NVDA foreground application appears, and still refuses playback when another application is active.

## [1.2.6] - 2026-09-17

### Fixed
- Application-lock target detection now uses NVDA's focused and foreground objects before falling back to the Windows foreground window.
- The add-on remembers the last focused non-NVDA application, so the target remains available after Macro Manager receives focus.
- Reopening an existing Macro Manager from another application refreshes the fallback target and its checkbox label.

## [1.2.5] - 2026-09-17

### Fixed
- Restored add-on interface translations by preserving the translation function installed by NVDA for this add-on instead of replacing it with NVDA's core translation function.
- Application locks now retain the application that was active before Macro Manager opened, including for legacy and imported macros whose saved data has no recorded-application metadata.
- Added regression coverage for add-on translation initialization and the edit/save/reload application-lock path with missing legacy metadata.

## [1.2.4] - 2026-09-17

### Added
- Local regression tests for recording hooks, safe-mode suppression, playback cleanup, application locks, macro validation, atomic persistence, bounded clipboard imports, and edited key hold durations.
- Explicit cleanup when NVDA disables or reloads the add-on.
- Complete German, Spanish, Turkish, and Portuguese (Portugal) interface catalogs, with localized documentation for every non-English language.
- Per-macro start delay with preset and custom decimal values; it runs once before the first event and remains independent of playback speed.

### Changed
- Safe recording now suppresses all captured physical keyboard events while preserving its dedicated stop gesture.
- Application-locked macros now fail closed when the foreground application cannot be identified and stop when focus changes.
- Application locks selected in the macro editor now preserve their target across saves, including legacy or imported macros without a recorded-application field.
- Dynamic NVDA shortcuts now resolve the current stored macro by ID at execution time, so loop-count, speed, event, and application-lock edits also take effect for shared/imported macros and cached shortcuts.
- Macro files and clipboard imports are normalized and size-bounded before use.
- Macro database updates use same-directory temporary files, backups, and atomic replacement.
- The event editor preserves the recorded key hold duration when converting between raw and linear events.
- Package metadata, user documentation, CI actions, Ruff, and Pyright checks were aligned with the project and version 1.2.4.

### Fixed
- Replaced the nonexistent NVDA core pump request with main-thread callbacks.
- Corrected 64-bit Windows hook and `SendInput` ctypes signatures and now report hook installation failures.
- Removed playback start races and ensured only keys injected by the active playback are released on cancellation or failure; physical Ctrl, Shift, Alt, Win, and NVDA shortcut modifiers are no longer released synthetically.
- Prevented stale or invalid macro IDs from creating invalid dynamic NVDA script names.
- Storage failures no longer produce false success announcements in the manager.
- Removed forced dark control colors so NVDA users keep native Windows and high-contrast theme behavior.

## [1.2.3] - 2026-06-30

### Fixed
- Packaging and store-submission metadata corrections following the AddonTemplate migration.

## [1.2.0] - 2026-06-29

### Added
- **Clipboard Sharing:** Easily copy and import macros directly via the system clipboard using Base64/Zlib text representation, allowing effortless macro sharing with the community.
- **AddonTemplate Migration:** Completely migrated the project to the official NVDA AddonTemplate.
- **Macro Editor (IDE) UI Revolution:** Transitioned the macro editor entirely to a professional, linear step-by-step framework. Delays and keys are no longer grouped into single messy lines. Instead, every action (Wait, Key Down, Key Up, Press) is an independent line that can be moved, edited, copied, or deleted individually.
- **Add Event Module:** Users can now dynamically inject new events (Wait delays or specific Key Strokes) at any point in an existing macro without needing to re-record.
- **Copy, Cut, and Paste Support:** Implemented a dedicated clipboard for macro events. You can now use standard `Ctrl+C`, `Ctrl+X`, and `Ctrl+V` shortcuts in the list to flawlessly duplicate or move steps around the macro.
- **Advanced List View Selection Setup:** The events list now safely supports clearing all selections using the `Escape` key, allowing you to instantly drop down to the end of the macro to paste or append events. `Ctrl+Space` is also natively supported to toggle selections easily with screen readers.
- **Advanced Dynamic Key Selection (`KeySelectDialog`):** When adding or editing a key, users can now capture real physical keypresses or select keys from a newly intelligent dropdown list.
- **Native Keyboard Mapping and Grouping:** The dropdown list seamlessly pulls native keyboard layouts (e.g., dynamically fetching characters like Ş, Ğ, or native symbols) directly via Windows API. Keys are neatly sorted alphabetically under specific semantic UI groups (`Letters`, `Punctuation`, `Numpad`, `Navigation`, `System`). NVDA strictly reads punctuation smoothly using hardcoded fallback labels like ". (Dot)", " (Quote)".
- **Deep i18n Localization:** All interface texts, internal lists, and warning messages are completely tied to Python `gettext` localization. Translations have been fully upgraded into `es`, `de`, and `tr` `.po`/`.mo` locale repositories.

### Changed
- Improved modifier key (Alt, Ctrl, Win, Shift) architecture: They are safely mapped as separate `Key Down` and `Key Up` events out of the box so multi-keypress hooks (like `Alt+Tab`) work perfectly.
- Cleaned up the confusing "Hold Time" texts on instant standard presses, simplifying playback visualization.
