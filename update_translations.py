"""Synchronize add-on gettext catalogs without requiring GNU gettext locally."""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

import polib


ROOT = Path(__file__).resolve().parent
SOURCE_FILES = (ROOT / "addon/globalPlugins/nvda_macro_manager.py", ROOT / "buildVars.py")
LOCALE_ROOT = ROOT / "addon/locale"

TURKISH_TRANSLATIONS = {
	"! (Exclamation mark)": "! (Ünlem işareti)",
	'" (Double quote)': '" (Çift tırnak)',
	"# (Number sign)": "# (Kare işareti)",
	"$ (Dollar sign)": "$ (Dolar işareti)",
	"% (Percent sign)": "% (Yüzde işareti)",
	"& (Ampersand)": "& (Ve işareti)",
	"' (Single quote)": "' (Tek tırnak)",
	"( (Left parenthesis)": "( (Sol parantez)",
	") (Right parenthesis)": ") (Sağ parantez)",
	"* (Asterisk)": "* (Yıldız)",
	"+ (Plus)": "+ (Artı)",
	", (Comma)": ", (Virgül)",
	"- (Hyphen / Minus)": "- (Tire / Eksi)",
	". (Dot)": ". (Nokta)",
	"/ (Slash)": "/ (Eğik çizgi)",
	": (Colon)": ": (İki nokta)",
	"; (Semicolon)": "; (Noktalı virgül)",
	"< (Less than)": "< (Küçüktür)",
	"= (Equals)": "= (Eşittir)",
	"> (Greater than)": "> (Büyüktür)",
	"? (Question mark)": "? (Soru işareti)",
	"@ (At sign)": "@ (Et işareti)",
	"[ (Left square bracket)": "[ (Sol köşeli parantez)",
	"\\ (Backslash)": "\\ (Ters eğik çizgi)",
	"] (Right square bracket)": "] (Sağ köşeli parantez)",
	"^ (Caret)": "^ (Düzeltme işareti)",
	"_ (Underscore)": "_ (Alt çizgi)",
	"` (Grave accent)": "` (Ters aksan)",
	"A macro is already playing.": "Bir makro zaten oynatılıyor.",
	"Alt": "Alt",
	"An accessible keyboard macro recorder, editor, and playback engine for NVDA.\nFeatures include safe recording, a multi-event editor, custom shortcuts, application locks, and speed controls.": "NVDA için erişilebilir bir klavye makrosu kayıt, düzenleme ve oynatma motoru.\nGüvenli kayıt, çok olaylı düzenleyici, özel kısayollar, uygulama kilitleri ve hız denetimleri içerir.",
	"Application key": "Uygulama tuşu",
	"Application Lock Security": "Uygulama Kilidi Güvenliği",
	"Backspace": "Geri Silme",
	"Cannot play this macro because its data is invalid.": "Verileri geçersiz olduğu için bu makro oynatılamıyor.",
	"Cannot enable the application lock because no target application is available. Record the macro in the target application and try again.": "Hedef uygulama bulunamadığı için uygulama kilidi etkinleştirilemiyor. Makroyu hedef uygulamada kaydedip yeniden deneyin.",
	"Caps Lock": "Büyük Harf Kilidi",
	"Could not delete the selected macros. See the NVDA log for details.": "Seçili makrolar silinemedi. Ayrıntılar için NVDA günlüğüne bakın.",
	"Could not save the macro. See the NVDA log for details.": "Makro kaydedilemedi. Ayrıntılar için NVDA günlüğüne bakın.",
	"Could not start macro recording. See the NVDA log for details.": "Makro kaydı başlatılamadı. Ayrıntılar için NVDA günlüğüne bakın.",
	"Could not update the macro. See the NVDA log for details.": "Makro güncellenemedi. Ayrıntılar için NVDA günlüğüne bakın.",
	"Ctrl": "Ctrl",
	"Delete": "Sil",
	"Down Arrow": "Aşağı Ok",
	"End": "Son",
	"Enter": "Enter",
	"Escape": "Kaçış",
	"Function keys": "İşlev tuşları",
	"Fixed foreground-application identification by using the process ID returned by NVDA's window helper instead of the thread ID.\nApplication-locked playback now identifies applications such as Audacity and Sound Forge correctly while retaining fail-closed security checks.": "NVDA'nın pencere yardımcısının döndürdüğü işlem kimliği, iş parçacığı kimliği yerine kullanılarak ön plan uygulamasının belirlenmesi düzeltildi.\nUygulama kilitli oynatma artık kapalı kalma ilkesini korurken Audacity ve Sound Forge gibi uygulamaları doğru tanıyor.",
	"Home": "Baş",
	"hold": "basılı tutma",
	"Insert": "Ekle",
	"Key Down": "Tuş Aşağı",
	"Key Up": "Tuş Yukarı",
	"Key updated.": "Tuş güncellendi.",
	"Left Arrow": "Sol Ok",
	"Letters": "Harfler",
	"Macro playback canceled.": "Makro oynatımı iptal edildi.",
	"Macro playback completed.": "Makro oynatımı tamamlandı.",
	"Macro playback failed. See the NVDA log for details.": "Makro oynatılamadı. Ayrıntılar için NVDA günlüğüne bakın.",
	"Macro stopped because the active application changed. Expected: '{target_app}', current: '{current_app}'.": "Etkin uygulama değiştiği için makro durduruldu. Beklenen: '{target_app}', geçerli: '{current_app}'.",
	"Navigation": "Gezinme",
	"Num Lock": "Sayı Kilidi",
	"Numpad": "Sayısal Tuş Takımı",
	"Numpad Add": "Sayısal Tuş Takımı Artı",
	"Numpad Decimal": "Sayısal Tuş Takımı Ondalık",
	"Numpad Divide": "Sayısal Tuş Takımı Bölü",
	"Numpad Enter": "Sayısal Tuş Takımı Enter",
	"Numpad Multiply": "Sayısal Tuş Takımı Çarpı",
	"Numpad Subtract": "Sayısal Tuş Takımı Eksi",
	"Numbers": "Rakamlar",
	"NVDA Macro Manager": "NVDA Makro Yöneticisi",
	"Page Down": "Sayfa Aşağı",
	"Page Up": "Sayfa Yukarı",
	"Pause": "Duraklat",
	"Please press the new key on your keyboard...\n(It will be captured automatically)": "Lütfen klavyenizdeki yeni tuşa basın...\n(Otomatik olarak yakalanacaktır)",
	"Press": "Bas ve Bırak",
	"Press a New Key": "Yeni Bir Tuşa Basın",
	"Print Screen": "Ekranı Yazdır",
	"Punctuation": "Noktalama",
	"Right Arrow": "Sağ Ok",
	"Scroll Lock": "Kaydırma Kilidi",
	"Shift": "Shift",
	"Space": "Boşluk",
	"Start Delay (seconds):": "Başlangıç Gecikmesi (saniye):",
	"Start Delay. This wait happens once before playback and is not affected by playback speed.": "Başlangıç Gecikmesi. Bu bekleme oynatmadan önce bir kez uygulanır ve oynatma hızından etkilenmez.",
	"System": "Sistem",
	"System and editing": "Sistem ve düzenleme",
	"Tab": "Sekme",
	"unknown": "bilinmiyor",
	"Up Arrow": "Yukarı Ok",
	"Windows": "Windows",
	"{ (Left brace)": "{ (Sol küme parantezi)",
	"| (Vertical bar)": "| (Dikey çizgi)",
	"} (Right brace)": "} (Sağ küme parantezi)",
	"~ (Tilde)": "~ (Tilde)",
}

CHANGELOG_MSGID = (
	"Fixed foreground-application identification by using the process ID returned by NVDA's window helper "
	"instead of the thread ID.\n"
	"Application-locked playback now identifies applications such as Audacity and Sound Forge correctly while "
	"retaining fail-closed security checks."
)

LOCALE_OVERRIDES = {
	"tr": TURKISH_TRANSLATIONS,
	"de": {
		CHANGELOG_MSGID: "Die Erkennung der Vordergrundanwendung wurde korrigiert, indem die von NVDAs Fensterhilfsfunktion zur\u00fcckgegebene Prozess-ID anstelle der Thread-ID verwendet wird.\nDie an eine Anwendung gebundene Wiedergabe erkennt nun Anwendungen wie Audacity und Sound Forge korrekt, w\u00e4hrend die sicherheitsorientierte Sperrlogik beibehalten wird.",
		"Start Delay (seconds):": "Startverzögerung (Sekunden):",
		"Start Delay. This wait happens once before playback and is not affected by playback speed.": "Startverzögerung. Diese Wartezeit wird einmal vor der Wiedergabe angewendet und nicht von der Wiedergabegeschwindigkeit beeinflusst.",
	},
	"es": {
		CHANGELOG_MSGID: "Se corrigió la identificación de la aplicación en primer plano usando el identificador de proceso devuelto por la función auxiliar de ventanas de NVDA en lugar del identificador de hilo.\nLa reproducción bloqueada a una aplicación ahora identifica correctamente programas como Audacity y Sound Forge, manteniendo las comprobaciones de seguridad que bloquean ante cualquier duda.",
		"Start Delay (seconds):": "Retardo inicial (segundos):",
		"Start Delay. This wait happens once before playback and is not affected by playback speed.": "Retardo inicial. Esta espera se aplica una vez antes de la reproducción y no se ve afectada por la velocidad de reproducción.",
	},
	"pt_PT": {
		CHANGELOG_MSGID: "Foi corrigida a identificação da aplicação em primeiro plano, utilizando o identificador do processo devolvido pela função auxiliar de janelas do NVDA em vez do identificador da thread.\nA reprodução bloqueada a uma aplicação identifica agora corretamente programas como o Audacity e o Sound Forge, mantendo as verificações de segurança que bloqueiam em caso de dúvida.",
		"Start Delay (seconds):": "Atraso inicial (segundos):",
		"Start Delay. This wait happens once before playback and is not affected by playback speed.": "Atraso inicial. Esta espera ocorre uma vez antes da reprodução e não é afetada pela velocidade de reprodução.",
	},
}


def extract_messages(path: Path) -> dict[str, list[tuple[str, int]]]:
	tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
	messages: dict[str, list[tuple[str, int]]] = {}
	for node in ast.walk(tree):
		if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "_":
			continue
		if (
			not node.args
			or not isinstance(node.args[0], ast.Constant)
			or not isinstance(node.args[0].value, str)
		):
			continue
		messages.setdefault(node.args[0].value, []).append((path.relative_to(ROOT).as_posix(), node.lineno))
	return messages


def load_catalog(path: Path) -> polib.POFile:
	if path.exists():
		return polib.pofile(str(path))
	return polib.POFile()


def synchronize_locale(
	language: str,
	messages: dict[str, list[tuple[str, int]]],
	turkish_lookup: dict[str, str],
) -> tuple[int, int]:
	po_path = LOCALE_ROOT / language / "LC_MESSAGES/nvda.po"
	mo_path = po_path.with_suffix(".mo")
	old_po = load_catalog(po_path)
	direct = {entry.msgid: entry.msgstr for entry in old_po if entry.msgstr and not entry.obsolete}
	translated_turkish = {
		entry.msgid: entry.msgstr for entry in old_po if entry.msgstr and not entry.obsolete
	}

	new_po = polib.POFile()
	new_po.metadata = dict(old_po.metadata)
	new_po.metadata.update(
		{
			"Project-Id-Version": "NVDAMacroManager 1.2.8",
			"Content-Type": "text/plain; charset=UTF-8",
			"Content-Transfer-Encoding": "8bit",
			"Language": language,
			"MIME-Version": "1.0",
			"PO-Revision-Date": datetime.now(UTC).strftime("%Y-%m-%d %H:%M+0000"),
		},
	)

	translated = 0
	for msgid in sorted(messages, key=str.casefold):
		msgstr = direct.get(msgid, "")
		if language in LOCALE_OVERRIDES and (not msgstr or msgid == CHANGELOG_MSGID):
			msgstr = LOCALE_OVERRIDES[language].get(msgid, msgstr)
		elif not msgstr:
			old_turkish_msgid = turkish_lookup.get(msgid)
			if old_turkish_msgid:
				msgstr = translated_turkish.get(old_turkish_msgid, "")
		entry = polib.POEntry(msgid=msgid, msgstr=msgstr, occurrences=messages[msgid])
		new_po.append(entry)
		translated += bool(msgstr)

	po_path.parent.mkdir(parents=True, exist_ok=True)
	new_po.save(str(po_path))
	new_po.save_as_mofile(str(mo_path))
	return translated, len(new_po)


def main() -> None:
	messages: dict[str, list[tuple[str, int]]] = {}
	for source in SOURCE_FILES:
		for msgid, occurrences in extract_messages(source).items():
			messages.setdefault(msgid, []).extend(occurrences)

	tr_path = LOCALE_ROOT / "tr/LC_MESSAGES/nvda.po"
	tr_po = load_catalog(tr_path)
	turkish_lookup = {entry.msgid: entry.msgstr for entry in tr_po if entry.msgstr and not entry.obsolete}
	for language in ("tr", "de", "es", "pt_PT"):
		translated, total = synchronize_locale(language, messages, turkish_lookup)
		print(f"{language}: {translated}/{total} translated; PO and MO updated")


if __name__ == "__main__":
	main()
