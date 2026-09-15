# Matematik Avı — Teslim Kontrol Listesi

Bu belge **senin** içindir (Luden Studio), müşteri için değil. Müşteriye giden
belge `docs/KURULUM.md`'dir.

Teslim modeli: **site üzerinden açık indirme yok.** İsteyen kişi siteden talep
açar; sen Drive linkini ve anahtarı e-postayla elden gönderirsin. Kimin hangi
anahtarı aldığı Lisans Merkezi'nin kayıtlarında durur.

---

## A. Paketi üret (sürüm başına bir kez)

```powershell
cd 01-Projects\Matematik_Avi
.venv\Scripts\python.exe build.py            # build\matematik.dist\
.venv\Scripts\python.exe build.py --kurucu   # kurucu + ZIP + SHA-256
```

Ön koşullar (bir kez):

- `~/.luden-lisans/urunler/matematik/icerik.key` var (Lisans Merkezi →
  Matematik Avı → *Anahtar çifti üret*). Yoksa build ilk adımda durur.
- `python/models/hand_landmarker.task` var (`cd python && python
  download_model.py`). Yoksa build durur (`--force` ile atlanabilir ama
  paket internetsiz açılışta el takibi yapamaz).
- `npx` (Node) kurulu — `javascript-obfuscator` onunla çekilir. Yoksa
  `--obfuscate-yok` ile geç; paket yine şifrelenir, yalnız JS okunabilir
  kalır (çözülürse).
- Inno Setup 6: `winget install JRSoftware.InnoSetup`.

1. Build çıktısında `[build] web paketi: web.pak (... KB, sifreli,
   paket_no=1)` satırını gör. `verify_dist` ham `web/` klasörünün dist'te
   **olmadığını** doğrular; varsa paket bozuktur.
2. `--kurucu` önce dist'i tarar: `config.json`, `calib.json`,
   `aktivasyon.dat`, `lisanslar.json` ya da `*.key` bulursa **durur**. Bu
   dosyalar normalde `%LOCALAPPDATA%`'da olur; dist'e düşmüşlerse
   `MATEMATIK_VERI_KOKU` ile test edilmiş ve unutulmuştur.
3. Sonunda yazdırılan **SHA-256** satırını kopyala. O özet e-postaya girecek.
4. Çıktılar: `dist\MatematikAvi-Setup-0.9.0-win64.exe` ve yanındaki `.zip`.
   **Müşteriye giden dosya ZIP'tir.**

> Sürüm numarası tek yerde: `surum.py`. Artırınca kurucu adı, EXE damgası ve
> "Program Ekle/Kaldır" kaydı birlikte değişir. İlk gerçek müşteri teslimi
> **1.0.0** olacak; 0.9.x kendi test kurulumlarını işaretler.

### Build sonrası doğrulama

```powershell
.venv\Scripts\python.exe -m pytest tests\test_build.py tests\test_kurucu.py
(Get-Item build\matematik.dist\"Matematik Avi.exe").VersionInfo   # CompanyName / ProductVersion dolu mu
Get-ChildItem build\matematik.dist -Directory | Select-Object Name  # ham "web" YOK, lisans_web VAR
```

Sonra kurucuyu **Program Files'a kur** ve sırayla dene:

| # | Adım | Beklenen |
|---|---|---|
| 1 | İlk açılış | Lisans penceresi gelir, oyun açılmaz |
| 2 | Pencereyi kapat | "gecerli bir lisans yok" mesaj kutusu; süreç biter |
| 3 | TEST anahtarı gir (Merkez → 1 dakika) | `%LOCALAPPDATA%\MatematikAvi\aktivasyon.dat` oluşur, kiosk açılır |
| 4 | Kiosk'ta F12 → Network | `/js/game.js?v=7` 200, olmayan yol 404 |
| 5 | Demo anahtarda köşe | Filigran görünür (`Kurum — tarih — #no`) |
| 6 | 1 dakika sonra yeniden aç | "Süreniz doldu" |
| 7 | Kalıcı anahtar | Filigran yok |
| 8 | Ctrl | Fare/el takibi geçişi, "FARE MODU" rozeti doğru |
| 9 | Kaldır → yeniden kur | Anahtar sorulmaz, kalibrasyon yerinde |
| 10 | Başlat menüsü → Kalibrasyon kısayolu | `--kalibrasyon` ile açılır, kamera/lisans kapısını atlamaz |

Elle: Windows saatini 5 gün geri al → "saat" mesajı. Kurulum klasörünü başka
makineye kopyala → "başka bilgisayara ait".

Kaynaktan `python matematik.py` → lisans **hiç sorulmaz**, `web/` diskten
servis edilir; geliştirme döngüsü değişmedi.

> **`build\...\Matematik Avi.exe`'yi doğrudan çalıştırarak test etme** —
> yanındaki aktivasyon senin geçerli aktivasyonundur, lisans ekranı hiç
> çıkmaz. Temiz test kurucudan geçer.

## B. Anahtar üret

```
01-Projects\LisansMerkezi\MERKEZ.bat
```

Key ver sekmesi → **Matematik Avı** → süre → kurum adı → *Yeni üret ve ver* →
`.dat olarak kaydet`.

- Süre seçimi kuruma göre: deneme için 7-14 gün, değerlendirme için 30 gün.
- Kurum adını yaz — oyundaki filigranda o görünür. Havuz anahtarı verirsen
  filigranda kurum yerine `Demo — #42` çıkar.
- Satılmış kurulum için **Kalıcı** seç: süre denetimi olmaz, filigran çıkmaz.

Anahtar **tek makineye** bağlanır (ilk kullanıldığı makineye). Müşteri
bilgisayar değiştirirse yeni anahtar üret; eskisini iptal etmen gerekmez.

## C. E-postayı gönder

Gönderilecek dört şey:

1. Drive linki (ZIP).
2. ZIP'in SHA-256 özeti.
3. `lisans.dat` (ek olarak) **veya** anahtar metni.
4. `docs/KURULUM.md` — PDF'e çevirip ekle ya da içeriğini e-postaya yapıştır
   (ZIP'in içinde `KURULUM.txt` olarak zaten gider).

E-postada mutlaka geçmesi gereken cümle: **"Windows mavi bir uyarı
gösterebilir; 'Daha fazla bilgi' → 'Yine de çalıştır' deyin."** Sertifika
satın alınmadığı için bu uyarı ilk kurulumlarda çıkar ve destek çağrılarının
en yaygın sebebidir (karar `KimyaLab/docs/TESLIM.md`'de alındı, burada aynen
geçerli).

## D. Kayıt

Lisans Merkezi anahtarı otomatik "verildi" olarak işaretler. Müşteri anahtarını
kaybederse Kayıtlar sekmesinden aynı anahtar yeniden görünür — yenisini üretme.

---

## Yeni sürüm çıkarken

1. `surum.py` içindeki `SURUM`'u artır.
2. A adımını tekrarla; yeni ZIP ve **yeni** SHA-256.
3. Eski anahtarlar çalışmaya devam eder — anahtar sürüme değil ürüne bağlıdır
   (yalnız `lisans.PAKET_NO` artırılırsa "bu anahtar programın eski bir sürümü
   için üretilmiş" mesajı çıkar; o zaman Merkez'de de `paket_no` artırılır ve
   dağıtılmış anahtarlar yenilenir).
4. Müşteri programı kaldırıp yeniden kurabilir; `%LOCALAPPDATA%\MatematikAvi`
   silinmediği için kalibrasyonu ve aktivasyonu yerinde kalır.

## Kabul edilen sınırlar

- Lisans **dosyasının** başka bir makinede yeniden aktive edilmesi
  engellenemez (çevrimdışı sistem). `son_kullanim_ts` mutlak tavanı bunu
  süreyle sınırlar.
- Anakart değişince yeniden aktivasyon gerekir (HMAC anahtarı birincil
  bileşenden türetilir).
- `web.pak` lisanslı kullanıcı tarafından çözülebilir — korunan şey lisansı
  **olmayan** kişinin içeriği görememesi. JS obfuscation ek maliyet, engel
  değil.
- Kiosk sistem tarayıcısında (Chrome/Edge `--app=`) açılır; tarayıcı yoksa
  varsayılan tarayıcıya düşer ve F11 gerekir.
- Ctrl fare modu kalıcı bir durum tutmaz: her açılışta el takibiyle başlar,
  operatörün yanlışlıkla bastığı bir Ctrl sergiyi fare moduna düşürebilir
  (rozet bunu görünür kılar, ama otomatik geri dönüş yoktur).

## Depo güvenliği (her teslimden bağımsız)

- `~/.luden-lisans/` **asla commit edilmez** — özel anahtar sızarsa herkes
  Matematik Avı anahtarı üretebilir.
- Anahtar çifti üretimi **geri alınamaz**; ürettikten hemen sonra Lisans
  Merkezi'nden *Depoyu yedekle*.
- Oyunun içinde hiçbir anahtar yoktur, yalnız açık anahtar durur
  (`lisans.ACIK_ANAHTAR_HEX`). EXE'yi parçalayan biri anahtar **üretemez**.
