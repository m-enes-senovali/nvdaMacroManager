# NVDAMacroManager (Moderne Makro-IDE und Automatisierungs-Engine)

**Entwickler:** Muhammet Enes Şenovalı
**Version:** 1.2.6

NVDA Macro Manager ist ein barrierefreier Tastaturmakro-Rekorder, Editor und Wiedergabemotor, der in den NVDA-Screenreader integriert ist. Er ist für wiederholbare Desktop-Abläufe vorgesehen, bei denen die Zielanwendung und die aufgezeichnete Tastenfolge bekannt sind.

## 🚀 Hauptfunktionen

* **Zwei Aufzeichnungsmodi (Live und sicher):** Im Live-Modus erreichen die Tasten während der Aufzeichnung die Anwendungen. Der sichere Modus unterdrückt physische Tastendrücke, bis Sie ihn mit `NVDA + Windows + Umschalt + R` beenden.
* **Dynamische NVDA-Tastenkürzel:** Gespeicherte Makros werden in NVDA eingebunden. Unter `Einstellungen → Eingaben → Makro-Manager` können Sie jedem Makro ein eigenes Tastenkürzel zuweisen.
* **Professionelle Makro-IDE (Ereigniseditor):**
  * **Linearer Ablauf:** Tasten und Wartezeiten sind eigenständige Schritte (Warten, Drücken, Taste drücken, Taste loslassen).
  * **Ereignis-Zwischenablage:** `Strg + C`, `Strg + X` und `Strg + V` kopieren oder verschieben Makroschritte.
  * **Rückgängig/Wiederholen:** `Strg + Z` und `Strg + Y` machen Änderungen rückgängig oder stellen sie wieder her.
  * **Ereignisse einfügen:** Neue Wartezeiten oder Tasten können an beliebiger Stelle ergänzt werden.
* **Intelligente Tastenerfassung:** Erfassen Sie eine physische Taste oder wählen Sie sie aus einer lokalisierten, vom Betriebssystem erzeugten Liste aus.
* **Windows-Eingabewiedergabe:** Die Wiedergabe verwendet die Windows-API `SendInput`. Geschützte, erhöhte, entfernte oder Spiele-Anwendungen können simulierte Eingaben ablehnen; Anti-Cheat-Kompatibilität wird nicht garantiert.
* **Geschwindigkeit, Startverzögerung und Wiederholungen:** Stellen Sie die Geschwindigkeit frei ein, wählen Sie eine geschwindigkeitsunabhängige Verzögerung vor dem ersten Ereignis, verwenden Sie sofortige Wiedergabe oder eine Endlosschleife.
* **Anwendungssperre:** Sperren Sie ein Makro an eine bestimmte Anwendung. Die Wiedergabe startet nicht, wenn die Anwendung nicht bestätigt werden kann, und stoppt bei einem Fokuswechsel.
* **Mehrsprachig:** Vollständige Oberflächenkataloge für Englisch, Türkisch, Spanisch, Deutsch und Portugiesisch (Portugal).

## ⌨️ Standardtastenkürzel

* **`NVDA + Windows + R`:** Startet oder beendet die Live-Aufzeichnung.
* **`NVDA + Windows + Umschalt + R`:** Startet oder beendet die sichere Aufzeichnung. Physische Tasten werden während der Aufzeichnung unterdrückt.
* **`NVDA + Windows + P`:** Gibt das zuletzt aufgezeichnete temporäre Makro wieder oder bricht eine laufende Wiedergabe ab.
* **`NVDA + Umschalt + M`:** Öffnet den Makro-Manager.

## 📦 Installation

1. Laden Sie die aktuelle `.nvda-addon`-Datei von [GitHub Releases](https://github.com/m-enes-senovali/nvdaMacroManager/releases) herunter.
2. Öffnen Sie die Datei bei laufendem NVDA und bestätigen Sie die Installation.
3. Starten Sie NVDA neu, wenn Sie dazu aufgefordert werden, und überprüfen Sie das Add-on unter **NVDA-Menü → Werkzeuge → Add-on-Store → Installierte Add-ons**.

NVDA 2023.1 oder neuer ist erforderlich. Wegen der verwendeten Windows-Tastatur-APIs wird nur Windows unterstützt.

## 🛠️ Verwendung

### 1. Makro schnell aufzeichnen

* Verwenden Sie `NVDA + Windows + R` für eine normale Aufzeichnung.
* Verwenden Sie `NVDA + Windows + Umschalt + R`, wenn die gedrückten Tasten während der Aufzeichnung keine Aktionen auslösen sollen.
* Beenden Sie die Aufzeichnung mit demselben Tastenkürzel und testen Sie das temporäre Makro mit `NVDA + Windows + P`.

### 2. Makros speichern und bearbeiten

Öffnen Sie den Manager mit `NVDA + Umschalt + M`, geben Sie einen Namen ein, wählen Sie Geschwindigkeit, Startverzögerung und Wiederholungsanzahl und speichern Sie das Makro. Die Startverzögerung wird einmal vor dem ersten Ereignis angewendet und nicht durch die Wiedergabegeschwindigkeit verändert.

Wählen Sie ein gespeichertes Makro und anschließend **Bearbeiten**:

* Wählen Sie mit `Umschalt` mehrere Ereignisse aus.
* Kopieren oder verschieben Sie Ereignisse mit `Strg + C`, `Strg + X` und `Strg + V`.
* Ändern Sie Wartezeiten oder erfasste Tasten.
* Fügen Sie mit **Ereignis hinzufügen** neue Schritte ein.

### 3. Eigene Tastenkürzel zuweisen

Öffnen Sie in NVDA `Einstellungen → Eingaben`, erweitern Sie **Makro-Manager**, wählen Sie das Makro und weisen Sie ihm ein Tastenkürzel zu.

## 🔒 Daten und Sicherheit

Gespeicherte Makros befinden sich als `nvda_macros.json` im aktiven NVDA-Konfigurationsordner. Aktualisierungen werden atomar geschrieben; die vorherige Datei bleibt als `nvda_macros.json.bak` erhalten. Datei- und Zwischenablageimporte werden vor der Verwendung geprüft und größenbegrenzt.

Die sichere Aufzeichnung unterdrückt physische Tastendrücke, die Wiedergabe führt jedoch echte Tastaturaktionen aus. Prüfen Sie importierte Makros, testen Sie sie zuerst in einer unkritischen Anwendung und verwenden Sie möglichst Anwendungssperren. Das Add-on kann Windows-Integritätsstufen, geschützte Anwendungen, Einschränkungen von Remotesitzungen oder Spieleschutzsysteme nicht umgehen.
