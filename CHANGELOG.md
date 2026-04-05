# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
