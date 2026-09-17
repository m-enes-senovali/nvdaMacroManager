# NVDAMacroManager (Modern Makro IDE ve Otomasyon Motoru)

**Geliştirici:** Muhammet Enes Şenovalı
**Sürüm:** 1.2.6

NVDA Macro Manager, NVDA ekran okuyucusuyla bütünleşen, erişilebilirlik odaklı bir klavye makrosu kayıt, düzenleme ve oynatma motorudur. Hedef uygulamanın ve kaydedilen tuş dizisinin bilindiği tekrarlanabilir masaüstü iş akışları için tasarlanmıştır.

## 🚀 Temel Özellikler

* **Çift Kayıt Motoru (Canlı ve Güvenli Mod):** Canlı modda tuşlar kaydedilirken uygulamalara iletilir. Güvenli mod, `NVDA + Windows + Shift + R` ile durdurulana kadar kaydedilen fiziksel tuşları uygulamalardan gizler.
* **Dinamik NVDA Kısayolları:** Kaydettiğiniz her bir makroyu NVDA sistemine otomatik olarak entegre eder. NVDA'in `Tercihler -> Girdi Hareketleri -> Makro Yöneticisi` menüsünden dilediğiniz makroya özel kısayol atayabilirsiniz. Arayüze girmeden makrolarınızı saniyeler içinde tetikleyin.
* **Profesyonel Makro IDE'si (Olay Düzenleyici):** Makrolarınızı profesyonel bir geliştirici gibi yönetin.
  * **Doğrusal İş Akışı:** Tuşlar ve bekleme süreleri temiz, bağımsız adımlara bölünmüştür (Bekle, Bas-Çek, Tuş Aşağı, Tuş Yukarı).
  * **Yerleşik Pano (Clipboard):** Makro adımlarını kopyalamak veya taşımak için standart `Ctrl + C`, `Ctrl + X` ve `Ctrl + V` kısayollarını tam destekler.
  * **Geri/İleri Al:** Hata mı yaptınız? `Ctrl + Z` (Geri Al) veya `Ctrl + Y` (İleri Al) ile anında düzeltin.
  * **Dinamik Olay Ekleme:** Kayıt sırasında bir tuşa basmayı mı unuttunuz? Baştan kaydetmeye gerek kalmadan makronun herhangi bir yerine yeni bekleme süreleri veya belirli tuş vuruşları ekleyin.
* **Akıllı Tuş Yakalama:** Yeni bir tuş eklerken veya düzenlerken klavyeden fiziksel olarak tuşa basabilir veya doğrudan işletim sisteminden çekilip yerelleştirilmiş akıllı listeden (Harfler, Noktalama İşaretleri, Numpad, Sistem Tuşları) seçim yapabilirsiniz.
* **Windows Girdi Oynatımı:** Klavye girdilerini Windows `SendInput` API'siyle oynatır. Korumalı, yönetici yetkili, uzak veya oyun uygulamaları benzetilmiş girdiyi reddedebilir; anti-cheat uyumluluğu garanti edilmez.
* **Hassas Hız, Başlangıç Gecikmesi ve Döngü Kontrolü:** Makroları 0.1'lik adımlarla (Örn: 1.3x) hızlandırabilir, ilk olaydan önce oynatma hızından bağımsız bir gecikme belirleyebilir, anında oynatabilir veya sonsuz döngüye alabilirsiniz.
* **Uygulama Kilidi (App-Binding):** Makroyu belirli bir uygulamaya kilitleyebilirsiniz. Uygulama doğrulanamazsa oynatma başlamaz; odak başka bir uygulamaya geçerse oynatma durur.
* **Çoklu Dil (i18n) Desteği:** İngilizce, Türkçe (`tr`), İspanyolca (`es`), Almanca (`de`) ve Portekizce (Portekiz) (`pt_PT`) için eksiksiz arayüz katalogları içerir.

## ⌨️ Varsayılan Kısayollar

* **`NVDA + Windows + R`** : **CANLI** makro kaydını başlatır veya durdurur. (Tuş vuruşlarınız işletim sisteminde işlem görür).
* **`NVDA + Windows + Shift + R`** : **GÜVENLİ** makro kaydını başlatır veya durdurur. Fiziksel tuşlar kayıt sırasında bastırılır; durdurma kısayolu kullanılabilir kalır.
* **`NVDA + Windows + P`** : Son kaydedilen (geçici) makroyu oynatır. **Oynatma devam ederken basılırsa işlemi anında iptal eden bir Acil Durum Freni (Kill Switch) işlevi görür.**
* **`NVDA + Shift + M`** : Makro Yöneticisi arayüzünü açar.

## 📦 Kurulum

1. [Projenin sürümler sayfasından](https://github.com/m-enes-senovali/nvdaMacroManager/releases) en güncel `.nvda-addon` paketini indirin.
2. NVDA çalışırken paketi açın ve kurulumu onaylayın.
3. İstendiğinde NVDA'yı yeniden başlatın. NVDA 2023.1 veya daha yeni bir sürüm gereklidir.

## 🛠️ Nasıl Kullanılır?

### 1. Hızlı Makro Kaydetme
* Yaptığınız işlemi anında ekranda görmek istiyorsanız `NVDA + Win + R` kullanın.
* Eğer klavyede tehlikeli tuşlara (`Delete`, `Alt+F4` vb.) basacaksanız ve bilgisayarınızın etkilenmesini istemiyorsanız `NVDA + Win + Shift + R` kullanın.
* Kaydı bitirmek için aynı kısayola tekrar basın. Kaydedilen bu geçici makroyu `NVDA + Win + P` ile hemen test edebilirsiniz.

### 2. Makroyu Kalıcı Hale Getirme ve IDE Kullanımı
Geçici makronuzu veritabanına kaydetmek için `NVDA + Shift + M` kısayoluyla Makro Yöneticisini açın. Burada makronuza isim verip hızını, başlangıç gecikmesini ve döngü sayısını ayarlayarak "Kaydet" butonuna basın. Başlangıç gecikmesi ilk olaydan önce yalnızca bir kez uygulanır ve oynatma hızından etkilenmez.

Listede kayıtlı bir makroyu seçip **Düzenle** dediğinizde IDE açılır:
* Olaylar listesinde `Shift` ile birden çok adımı seçebilirsiniz.
* Seçili adımları `Ctrl + C` ile kopyalayıp, makronun farklı bir yerine `Ctrl + V` ile yapıştırabilirsiniz.
* Gecikme sürelerini topluca değiştirebilir veya yanlış basılan bir tuşu güncelleyebilirsiniz.
* "Olay Ekle" butonu ile makronun arasına yepyeni tuşlar veya bekleme süreleri enjekte edebilirsiniz.

### 3. Özel Kısayol Atama
Makronuzu kaydettikten sonra NVDA menüsünden `Tercihler -> Girdi Hareketleri` yolunu izleyin. Listeden **Makro Yöneticisi** kategorisini bulun. Orada kaydettiğiniz makronun adını göreceksiniz. Ekle butonuna basarak dilediğiniz tuş kombinasyonunu atayın.

## 🔒 Veri ve Güvenlik

Kayıtlı makrolar etkin NVDA yapılandırma dizininde tutulur. Yazımlar atomik yapılır ve önceki dosya `.bak` yedeği olarak saklanır. İçe aktarılan makroları inceleyin, önce kritik olmayan bir uygulamada deneyin ve mümkün olduğunda uygulama kilidi kullanın. Bazı korumalı, yönetici yetkili, uzak veya oyun uygulamaları benzetilmiş girdiyi reddedebilir.
