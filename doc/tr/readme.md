# NVDAMacroManager (Modern Makro Yöneticisi)

**Geliştirici:** Muhammet Enes Şenovalı
**Sürüm:** 1.0.2

NVDA Macro Manager, erişilebilirliği merkezine alan, işletim sistemi seviyesinde (low-level) çalışan, yüksek performanslı ve tamamen NVDA entegreli bir makro kayıt, düzenleme ve oynatma motorudur. Oyunlardan günlük ofis işlerine kadar tüm tekrarlayan görevlerinizi kusursuzca otomatikleştirir.

## 🚀 Temel Özellikler

* **Çift Kayıt Motoru (Canlı ve Güvenli Mod):** Makrolarınızı isterseniz ekranda görerek (Canlı), isterseniz de sistemden tamamen gizleyerek (Güvenli Mod) kaydedebilirsiniz. Güvenli modda bastığınız tuşlar işletim sistemine iletilmez; böylece masaüstünde gezinirken veya makro kaydederken yanlışlıkla dosyalarınız silinmez, pencereleriniz kapanmaz.
* **Dinamik Kısayol Atamaları:** Kaydettiğiniz her bir makroya NVDA'in `Tercihler -> Girdi Hareketleri -> Makro Yöneticisi` menüsünden dilediğiniz özel kısayolu atayabilirsiniz. Arayüze girmeden makrolarınızı saniyeler içinde tetikleyin.
* **Gelişmiş Makro IDE'si (Kurgu Masası):** * Kaydedilen tuşlar "Bas-Çek" olarak akıllıca birleştirilerek okunabilirlik artırılır.
  * **Çoklu Seçim:** Shift tuşuyla birden fazla olayı seçip toplu gecikme süresi atayabilirsiniz.
  * **Hızlandırıcılar:** `Delete` ile olayları anında silebilir, `Ctrl + Yukarı/Aşağı Ok` ile makro adımlarının sırasını değiştirebilirsiniz.
  * **Geri/İleri Al:** Düzenleme yaparken hata yaparsanız `Ctrl + Z` ile geri alabilir, `Ctrl + Y` ile ileri alabilirsiniz.
* **Oyun Uyumlu (Anti-Cheat Bypass):** Tuşları donanım kodlarıyla (ScanCode) göndererek oyunların güvenlik sistemlerine takılmadan çalışır.
* **Hassas Hız ve Döngü Kontrolü:** Makroları 0.1'lik adımlarla (Örn: 1.3x) hızlandırabilir, gecikmesiz (0) oynatabilir veya sonsuz döngüye alabilirsiniz.
* **Acil Durum Freni (Kill Switch):** Kontrolden çıkan bir makroyu oynatma kısayoluna tekrar basarak anında durdurabilirsiniz.
* **Uygulama Kilidi (App-Binding):** Makrolarınızı sadece belirli uygulamalarda (.exe) çalışacak şekilde kilitleyebilirsiniz.

## ⌨️ Varsayılan Kısayollar

* **`NVDA + Windows + R`** : **CANLI** makro kaydını başlatır veya durdurur. (Tuş vuruşlarınız işletim sisteminde işlem görür).
* **`NVDA + Windows + Shift + R`** : **GÜVENLİ (GÖLGE)** makro kaydını başlatır veya durdurur. (Kayıt sırasında bastığınız tuşlar sistemden gizlenir, bilgisayarınızda hiçbir işlem gerçekleşmez).
* **`NVDA + Windows + P`** : Son kaydedilen (geçici) makroyu oynatır. **Oynatma devam ederken basılırsa işlemi anında iptal eder.**
* **`NVDA + Shift + M`** : Makro Yöneticisi arayüzünü açar.

## 🛠️ Nasıl Kullanılır?

### 1. Hızlı Makro Kaydetme
* Yaptığınız işlemi anında ekranda görmek istiyorsanız `NVDA + Win + R` kullanın. 
* Eğer klavyede tehlikeli tuşlara (`Delete`, `Alt+F4` vb.) basacaksanız ve bilgisayarınızın etkilenmesini istemiyorsanız `NVDA + Win + Shift + R` kullanın.
* Kaydı bitirmek için aynı kısayola tekrar basın. Kaydedilen bu geçici makroyu `NVDA + Win + P` ile hemen test edebilirsiniz.

### 2. Makroyu Kalıcı Hale Getirme ve IDE Kullanımı
Geçici makronuzu veritabanına kaydetmek için `NVDA + Shift + M` kısayoluyla Makro yöneticisini açın. Burada makronuza isim verip, hızını veya döngüsünü ayarlayarak "Kaydet" butonuna basın.

Listede kayıtlı bir makroyu seçip **Düzenle** dediğinizde IDE açılır. Burada:
* Olaylar listesinde `Shift` ile birden çok tuşu seçebilirsiniz.
* Seçili tuşların bekleme sürelerini (milisaniye cinsinden) düzenleyebilirsiniz.
* İstenmeyen tuşları `Delete` ile silebilirsiniz.
* Hata yaparsanız `Ctrl + Z` ile işleminizi anında geri alabilirsiniz.

### 3. Özel Kısayol Atama
Makronuzu kaydettikten sonra NVDA menüsünden `Tercihler -> Girdi Hareketleri` yolunu izleyin. Listeden **Makro Yöneticisi** kategorisini bulun. Orada kaydettiğiniz makronun adını göreceksiniz. Ekle butonuna basarak dilediğiniz tuş kombinasyonunu atayın.