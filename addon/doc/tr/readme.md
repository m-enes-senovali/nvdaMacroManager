# NVDAMacroManager (Modern Makro IDE ve Otomasyon Motoru)

**Geliştirici:** Muhammet Enes Şenovalı  
**Sürüm:** 1.0.3  

NVDA Macro Manager, erişilebilirliği merkezine alan, işletim sistemi seviyesinde (low-level) çalışan, yüksek performanslı bir makro kayıt, düzenleme ve oynatma motorudur. Oyunlardaki karmaşık kombolardan günlük ofis işlerinize kadar tüm tekrarlayan görevlerinizi, NVDA ekran okuyucusuna tam entegre bir şekilde kusursuzca otomatikleştirir.

## 🚀 Temel Özellikler

* **Çift Kayıt Motoru (Canlı ve Güvenli Mod):** Makrolarınızı isterseniz ekranda görerek (Canlı), isterseniz de sistemden tamamen gizleyerek (Güvenli Mod) kaydedebilirsiniz. Güvenli modda bastığınız tuşlar işletim sistemine iletilmez; böylece masaüstünde gezinirken veya makro kaydederken yanlışlıkla dosyalarınız silinmez, pencereleriniz kapanmaz.
* **Dinamik NVDA Kısayolları:** Kaydettiğiniz her bir makroyu NVDA sistemine otomatik olarak entegre eder. NVDA'in `Tercihler -> Girdi Hareketleri -> Makro Yöneticisi` menüsünden dilediğiniz makroya özel kısayol atayabilirsiniz. Arayüze girmeden makrolarınızı saniyeler içinde tetikleyin.
* **Profesyonel Makro IDE'si (Olay Düzenleyici):** Makrolarınızı profesyonel bir geliştirici gibi yönetin.
  * **Doğrusal İş Akışı:** Tuşlar ve bekleme süreleri temiz, bağımsız adımlara bölünmüştür (Bekle, Bas-Çek, Tuş Aşağı, Tuş Yukarı).
  * **Yerleşik Pano (Clipboard):** Makro adımlarını kopyalamak veya taşımak için standart `Ctrl + C`, `Ctrl + X` ve `Ctrl + V` kısayollarını tam destekler.
  * **Geri/İleri Al:** Hata mı yaptınız? `Ctrl + Z` (Geri Al) veya `Ctrl + Y` (İleri Al) ile anında düzeltin.
  * **Dinamik Olay Ekleme:** Kayıt sırasında bir tuşa basmayı mı unuttunuz? Baştan kaydetmeye gerek kalmadan makronun herhangi bir yerine yeni bekleme süreleri veya belirli tuş vuruşları ekleyin.
* **Akıllı Tuş Yakalama:** Yeni bir tuş eklerken veya düzenlerken klavyeden fiziksel olarak tuşa basabilir veya doğrudan işletim sisteminden çekilip yerelleştirilmiş akıllı listeden (Harfler, Noktalama İşaretleri, Numpad, Sistem Tuşları) seçim yapabilirsiniz.
* **Oyun ve Anti-Cheat Uyumlu:** Tuşları donanım seviyesinde (SendInput API ve ScanCode) göndererek oyunların güvenlik sistemlerine takılmadan kusursuz çalışır.
* **Hassas Hız ve Döngü Kontrolü:** Makroları 0.1'lik adımlarla (Örn: 1.3x) hızlandırabilir, anında (0 gecikme) oynatabilir veya sonsuz döngüye alabilirsiniz.
* **Uygulama Kilidi (App-Binding):** Kritik hataları önlemek için makrolarınızı sadece belirli uygulamalarda (.exe) çalışacak şekilde kilitleyebilirsiniz.
* **Çoklu Dil (i18n) Desteği:** Yerleşik olarak Türkçe (`tr`), İngilizce (`en`), İspanyolca (`es`) ve Almanca (`de`) dillerini destekler.

## ⌨️ Varsayılan Kısayollar

* **`NVDA + Windows + R`** : **CANLI** makro kaydını başlatır veya durdurur. (Tuş vuruşlarınız işletim sisteminde işlem görür).
* **`NVDA + Windows + Shift + R`** : **GÜVENLİ (GÖLGE)** makro kaydını başlatır veya durdurur. (Kayıt sırasında bastığınız tuşlar sistemden gizlenir, bilgisayarınızda hiçbir işlem gerçekleşmez).
* **`NVDA + Windows + P`** : Son kaydedilen (geçici) makroyu oynatır. **Oynatma devam ederken basılırsa işlemi anında iptal eden bir Acil Durum Freni (Kill Switch) işlevi görür.**
* **`NVDA + Shift + M`** : Makro Yöneticisi arayüzünü açar.

## 🛠️ Nasıl Kullanılır?

### 1. Hızlı Makro Kaydetme
* Yaptığınız işlemi anında ekranda görmek istiyorsanız `NVDA + Win + R` kullanın. 
* Eğer klavyede tehlikeli tuşlara (`Delete`, `Alt+F4` vb.) basacaksanız ve bilgisayarınızın etkilenmesini istemiyorsanız `NVDA + Win + Shift + R` kullanın.
* Kaydı bitirmek için aynı kısayola tekrar basın. Kaydedilen bu geçici makroyu `NVDA + Win + P` ile hemen test edebilirsiniz.

### 2. Makroyu Kalıcı Hale Getirme ve IDE Kullanımı
Geçici makronuzu veritabanına kaydetmek için `NVDA + Shift + M` kısayoluyla Makro Yöneticisini açın. Burada makronuza isim verip, hızını veya döngüsünü ayarlayarak "Kaydet" butonuna basın.

Listede kayıtlı bir makroyu seçip **Düzenle** dediğinizde IDE açılır:
* Olaylar listesinde `Shift` ile birden çok adımı seçebilirsiniz.
* Seçili adımları `Ctrl + C` ile kopyalayıp, makronun farklı bir yerine `Ctrl + V` ile yapıştırabilirsiniz.
* Gecikme sürelerini topluca değiştirebilir veya yanlış basılan bir tuşu güncelleyebilirsiniz.
* "Olay Ekle" butonu ile makronun arasına yepyeni tuşlar veya bekleme süreleri enjekte edebilirsiniz.

### 3. Özel Kısayol Atama
Makronuzu kaydettikten sonra NVDA menüsünden `Tercihler -> Girdi Hareketleri` yolunu izleyin. Listeden **Makro Yöneticisi** kategorisini bulun. Orada kaydettiğiniz makronun adını göreceksiniz. Ekle butonuna basarak dilediğiniz tuş kombinasyonunu atayın.