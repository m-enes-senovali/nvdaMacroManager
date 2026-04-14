import os

dosyalar = [
    "README.md",
    "doc/tr/readme.md",
    "doc/en/readme.md",
    "addon/globalPlugins/nvda_macro_manager.py"
]

for dosya in dosyalar:
    if os.path.exists(dosya):
        with open(dosya, 'r', encoding='utf-8') as f:
            icerik = f.read()
        
        # Satır sonu boşluklarını temizle
        temiz_satirlar = [satir.rstrip() for satir in icerik.splitlines()]
        # En sona standart bir boş satır ekle
        temiz_icerik = '\n'.join(temiz_satirlar) + '\n'
        
        with open(dosya, 'w', encoding='utf-8') as f:
            f.write(temiz_icerik)
        print(f"{dosya} basariyla temizlendi!")