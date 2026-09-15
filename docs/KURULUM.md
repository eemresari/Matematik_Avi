# Matematik Avı — Kurulum ve Anahtar Kılavuzu

Bu belge Matematik Avı'yı ilk kez kuran kişi içindir. Teknik bilgi gerektirmez.

**Gereken:** Windows 10 veya 11 (64-bit), yönetici hakkı olan bir hesap ve
Google Chrome ya da Microsoft Edge (Windows'ta hazır gelir).
İnternet **gerekmez** — oyun da anahtar denetimi de tamamen çevrimdışı çalışır.

---

## 1. Dosyayı indirin ve açın

Size e-postayla iki şey gönderildi:

1. Bir **indirme bağlantısı** (Google Drive) — içinde
   `MatematikAvi-Setup-0.9.0-win64.zip` var.
2. Bir **anahtar** — ya `lisans.dat` adlı bir dosya ya da `LDN1.` ile başlayan
   uzun bir metin.

ZIP'i indirin, sağ tık → **Tümünü ayıkla**. İçinden
`MatematikAvi-Setup-0.9.0-win64.exe` çıkar.

> **Dosyanın bozulmadığını doğrulamak isterseniz** (isteğe bağlı): e-postadaki
> SHA-256 özetiyle karşılaştırın. PowerShell'de:
> ```powershell
> Get-FileHash .\MatematikAvi-Setup-0.9.0-win64.zip -Algorithm SHA256
> ```
> Çıkan değer e-postadakiyle aynı olmalı.

## 2. "Windows bilgisayarınızı korudu" uyarısı

Kurucuya çift tıkladığınızda mavi bir SmartScreen penceresi çıkabilir. Bu bir
virüs uyarısı **değildir**: Windows, henüz çok sayıda kişi tarafından
indirilmemiş yeni dosyalar için bunu gösterir.

**Yapılacak:** pencerede **Daha fazla bilgi** yazısına tıklayın, sonra çıkan
**Yine de çalıştır** düğmesine basın.

Doğru dosyada olduğunuzu şuradan teyit edebilirsiniz: aynı pencerede
*Yayımcı* satırında **Luden Studio** yazar.

## 3. Kurulum

Kurucu sizi birkaç adımda yönlendirir. Varsayılanları kabul etmeniz yeterli:

- Kurulum yeri: `C:\Program Files\Luden Studio\Matematik Avi`
- Başlat menüsüne kısayol eklenir (ayrıca bir **Kalibrasyon** kısayolu da
  gelir); isterseniz masaüstüne de.

Kurulum bitince oyunu Başlat menüsünden **Matematik Avi** ile açarsınız.

## 4. Anahtarı girme

İlk açılışta **Matematik Avi — Lisans** penceresi gelir. İki yol var, ikisi de
aynı sonuca varır:

- **Lisans dosyası seç...** → size gönderilen `lisans.dat` dosyasını seçin.
- Ya da anahtar metnini (`LDN1.` ile başlayan uzun satır) kutuya **yapıştırıp**
  **Anahtarı kullan** deyin.

Anahtar kabul edilirse pencere kapanır ve oyun tam ekran açılır. Anahtar bu
bilgisayara bağlanır; her açılışta yeniden girmeniz **gerekmez**.

## 5. Kalibrasyon (projeksiyon + kamera yerleştirildikten sonra, bir kez)

Başlat menüsünden **Matematik Avi - Kalibrasyon**'a tıklayın. Tam ekran
projeksiyonda sırayla 3×3 = 9 hedef noktası belirir; oyuncu her hedefi eliyle
~1.5 saniye sabit tutar. 9 nokta sonrası doğrulama ekranı gelir — hata **<%3**
ise *İYİ*. **A/Enter** ile kaydedin, **R** ile baştan başlayın, **Esc** ile
iptal edin.

## 6. Kamera var mı, yok mu? (Ctrl fare modu)

Oyun her zaman kamerayı açmaya çalışır, ama kamerasız bir demo/tanıtım
bilgisayarında da çalışır: oyun içindeyken **Ctrl** tuşuna basmak fare ve el
takibi arasında geçiş yapar. Ekranın bir köşesinde küçük bir **"FARE MODU"**
rozeti belirir; tekrar Ctrl'e basınca el takibine döner.

Deneme anahtarıyla açılan oyunda ekranın köşesinde kurum adı ve son kullanım
tarihi yazar; satın alınan sürümde bu yazı yoktur.

Oyundan çıkmak için **Esc**.

---

## Hata mesajları ne anlama geliyor?

| Pencerede yazan | Anlamı | Ne yapmalı |
|---|---|---|
| Bu bilgisayarda kayıtlı bir anahtar yok | Normal ilk açılış | Anahtarınızı girin |
| Süreniz doldu | Anahtarın geçerlilik süresi bitti | Bizden yeni anahtar isteyin |
| Bu kurulum başka bir bilgisayara ait | Anahtar başka makineye bağlanmış | O makine için verilen anahtar burada çalışmaz; yeni anahtar isteyin |
| Sistem saati geri alınmış görünüyor | Bilgisayarın tarihi geriye çekilmiş | Windows saatini doğru tarihe getirip programı yeniden açın |
| Bu anahtar geçerli değil | Metin eksik/bozuk kopyalanmış olabilir | Anahtarın tamamını, başındaki `LDN1.` dahil kopyalayın |
| Bu anahtar Matematik Avı için değil | Başka bir oyunun anahtarı | Doğru anahtarı isteyin |
| Bu anahtar programın eski bir sürümü için üretilmiş | Program güncellendi, anahtar eski | Bizden bu sürüm için anahtar isteyin |

## Sık sorulanlar

**Anahtar neden bu bilgisayara bağlanıyor?**
Anahtar süreli olduğu için, ilk kullanıldığı makineye bağlanır. Bilgisayar
değiştirirseniz bize yazın, yeni bir anahtar üretiriz.

**Bilgisayarı formatlarsam / donanım değiştirirsem?**
Küçük değişiklikler (RAM, ekran kartı) sorun çıkarmaz. Anakart veya disk
değişirse "başka bilgisayara ait" mesajı gelebilir; yeni anahtar isteyin.

**İnternet gerekiyor mu?**
Hayır. Ne kurulum ne de oyun internete bağlanır — fontlar da dahil her şey
pakete gömülüdür.

**Oyun açıldı ama pencere boş / siyah?**
Chrome veya Edge kurulu olmalı; ikisi de yoksa varsayılan tarayıcı açılır ve
tam ekran için **F11**'e basmanız gerekir.

**Ayarlarım nerede duruyor?**
Kalibrasyon ve anahtar kaydı `%LOCALAPPDATA%\MatematikAvi` klasöründedir.
Programı kaldırdığınızda bu klasör **silinmez** — yeniden kurunca
kalibrasyonunuz yerinde durur. Tamamen temizlemek isterseniz klasörü elle
silin.

**Nasıl kaldırırım?**
Ayarlar → Uygulamalar → **Matematik Avi** → Kaldır.

## Destek

Sorun devam ederse hata penceresinin fotoğrafıyla birlikte bize yazın.
