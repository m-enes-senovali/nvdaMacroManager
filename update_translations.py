import polib

po_path = "addon/locale/tr/LC_MESSAGES/nvda.po"
mo_path = "addon/locale/tr/LC_MESSAGES/nvda.mo"

with open(po_path, "r", encoding="utf-8") as f:
	content = f.read()

bad_str = (
	'msgstr ""\\n"Yeni bekleme süresini milisaniye (ms) cinsinden girin:\\n"\\n"(Örnek: 1 saniye için 1000)"'
)
good_str = (
	'msgstr ""\n"Yeni bekleme süresini milisaniye (ms) cinsinden girin:\\n"\n"(Örnek: 1 saniye için 1000)"'
)
content = content.replace(bad_str, good_str)

with open(po_path, "w", encoding="utf-8") as f:
	f.write(content)

po = polib.pofile(po_path)

translations = {
	"No valid macro code found in clipboard.": "Panoda geçerli bir makro kodu bulunamadı.",
	"Invalid macro format in clipboard.": "Panodaki makro formatı geçersiz.",
	"Failed to decode macro from clipboard.": "Panodaki makro çözümlenemedi.",
	"Import from Clipboard": "Panodan İçe Aktar",
	"Copy to Clipboard": "Panoya Kopyala",
	"Macro '{name}' copied to clipboard.": "Makro '{name}' panoya kopyalandı.",
	"Failed to copy macro to clipboard.": "Makro panoya kopyalanamadı.",
	"Imported macro: {name}": "İçe aktarılan makro: {name}",
	"Import File": "Dosyadan İçe Aktar",
	"Export File": "Dosyaya Dışa Aktar",
}

for msgid, msgstr in translations.items():
	entry = po.find(msgid)
	if entry:
		entry.msgstr = msgstr
	else:
		entry = polib.POEntry(msgid=msgid, msgstr=msgstr)
		po.append(entry)

po.save(po_path)
po.save_as_mofile(mo_path)
print("Translations updated successfully.")
