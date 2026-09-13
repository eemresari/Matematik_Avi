# Matematik Avı — lisans + EXE + kurucu hattı (OYUN-ENTEGRASYON-PLANI uygulaması)

## Context

`LisansMerkezi/docs/OYUN-ENTEGRASYON-PLANI.md` KimyaLab'da uçtan uca uygulanmış
demo→EXE→lisans hattının ürüne özel olmayan tarifi. SprayTarih (2026-09-11) ve
Aican (2026-09-12) bu hattı aldı; **Matematik Avı sıradaki üründür** ve şu an
Merkez'de `etkin: False` (`LisansMerkezi/urunler.py:36`).

Planın §12'si Matematik Avı için "Unity kalırsa lisans kapısı atlanır, önce web
göçünü bitir" diyordu. **Göç bitmiş.** Kod taraması: `web/js/{game,lens,tokens,
input,questions,leaderboard,calibration}.js` (1417 satır) gerçek oyun;
`python/net/ws_sender.py` köprüsü çalışıyor; `python/config.json` →
`net.transport = "ws"`; `start-kiosk.ps1` Unity'ye hiç dokunmuyor. `unity/`
2026-06-14'ten beri donmuş. Yani §12'nin **önerdiği yol açık**: KimyaLab/
SprayTarih hattı birebir uygulanabilir.

Hedef: müşteriye Drive linkiyle gidebilen, internetsiz kurulan, lisans
anahtarıyla açılan, içeriği şifreli tek bir Windows kurucusu.

**En yakın şablon SprayTarih'tir** (Python CV + web frontend + Chrome `--app` +
WS köprüsü + mediapipe). Matematik Avı'nın mimarisi onunla neredeyse birebir;
KimyaLab'a değil, SprayTarih'e bakılacak.

---

## Faz 0 — kapsam cevapları (plan §1)

| Soru | Matematik Avı'nın cevabı | Sonuç |
|---|---|---|
| **S1 — oyun mantığı hangi dilde?** | **JS/web.** Soru havuzu ve tuzak üretimi `web/js/questions.js` (200 satır), token alanı `tokens.js` (303), tur akışı `game.js` (346). Python yalnız CV. | **§4 içerik paketi ZORUNLU** |
| **S2 — arayüz nasıl açılıyor?** | Sistem Chrome'u, `--app=` + `--start-fullscreen` (`start-kiosk.ps1:88-100`). pywebview yok. | SprayTarih deseni: **oyun Chrome'da, lisans ekranı pywebview'de** |
| **S3 — donanım var mı?** | **Var** — webcam + MediaPipe HandLandmarker, ayrıca projeksiyon kalibrasyonu (`mapping/calibrate.py`, `calib.json`). | Lisans kapısı **kamera açılmadan önce** |

### Plandan üç bilinçli sapma (kullanıcı kararı, 2026-09-12)

1. **§10.3-10.6 mod seçim penceresi YOK.** `mod.json` yazılmayacak, açılışta
   soru sorulmayacak. Yerine: **oyun içinde `Ctrl` tuşu fare modunu açıp
   kapatır** (KimyaLab'ın blok-koyma modu gibi). Gerekçe: demo laptopunda da
   dahili webcam var, SprayTarih'in "kamera var mı" otomatik algılaması burada
   ayırt edemez; açık bir pencere ise sergi kurulumunu her sürümde bir kez
   rahatsız eder. Ctrl ikisini de çözer, hiçbir kalıcı durum tutmaz.
   - **Tuş çakışması kontrol edildi (§10.2 TUZAK):** web katmanında bağlı tek
     tuş `Escape` (`web/js/game.js:330`). `Ctrl` serbest.
2. **Unity tamamen temizlenecek.** Kullanıcı kararı: "oyunun Unity'yle hiçbir
   bağı kalmamış olmalı". `unity/` + OSC hattı siliniyor (aşağıda G1).
3. **Sıralama:** önce **G0 build spike** (Nuitka + mediapipe), sonra tam hat.

---

## Mevcut durum — neyin olmadığı

Matematik Avı'nda **hiçbiri yok**: `paths.py`, `surum.py`, `build.py`,
`installer/`, `tests/` (otomatik test sayısı **0**), lisans dosyaları, tek
giriş noktası. Dağıtım modeli "kaynak + `.bat` çift tıkla"; başlatmayı
`start-kiosk.ps1` üç ayrı süreç açarak yapıyor. Yani SprayTarih'te hazır olan
altyapının çoğu sıfırdan kurulacak — iş kalemlerinin yarısı lisans değil,
**paketlenebilirlik** işidir.

Ayrıca üç açık eksik bulundu:

- **Fontlar Google Fonts CDN'inden geliyor** (`web/index.html:7-9`: Baloo 2,
  JetBrains Mono, Space Grotesk). Plan §11.1 müşteriye "**internet gerekmez**"
  sözü verir; internetsiz sergide bugün tofu/yanlış metrik çıkar. Yerele
  alınacak.
- **Sorgu dizisi tuzağı canlı** (§4.2): `index.html:147-153` script'leri
  `?v=4`, `?v=6` ekiyle çağırıyor. Paketten servis eden yol çözücü sorguyu
  atmazsa oyun boş ekran açar.
- **`models/hand_landmarker.task` (7,8 MB) çalışma anında indiriliyor**
  (`python/download_model.py`). Internetsiz kurulumda EXE'nin yanına gömülmeli
  (Aican'ın Whisper modeliyle aynı karar).

---

## G0 — Build spike (ÖNCE BU, kod yazmadan)

**Soru:** mediapipe + opencv + websockets bağımlılıklarıyla `python/main.py`
Nuitka **standalone** olarak derlenip, çıkan EXE kamerayı açıp `.task` modelini
yükleyebiliyor mu?

Risk düşük ama sıfır değil: SprayTarih `tools/build_exe.py:407-477` zaten
`--include-package-data=mediapipe` ile derliyor, yani desen kanıtlı. Bilinmeyen
Matematik Avı'nın mediapipe **0.10.35** sürümü ve `HandLandmarker` LIVE_STREAM
modunun donmuş ortamda çalışması.

Adımlar:
1. Geçici `spike_build.py` — SprayTarih'in Nuitka komutunu kopyala, hedef
   `python/main.py`, `--standalone --windows-console-mode=force`,
   `--include-package-data=mediapipe`, `--include-package-data=cv2`,
   `--include-data-files=python/models/hand_landmarker.task=models/hand_landmarker.task`.
2. `dist/main.dist/main.exe --no-preview` çalıştır, `tools/ws_sniff.py` ile
   kare geliyor mu bak.
3. **Çıktı: kısa bir devir notu** → `docs/plans/2026-09-12-G0-build-spike.md`
   (Aican'daki `2026-09-11-G0-build-spike-devir.md` deseni): ne derlendi, dist
   boyutu, hangi bayrak gerekti, kalan tuzaklar.
4. Spike dosyaları commit edilmez; öğrenilen bayraklar G8'de gerçek
   `build.py`'ye geçer.

**cp1254 TUZAĞI (§9.6) daha spike'ta devreye alınır:** spike script'inin ilk
satırı `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`. Aksi halde
derleme 3 dakika sonra `UnicodeEncodeError` ile sebebi görünmeden durur.

---

## G1 — Unity ve OSC kalıntılarının temizliği + test altyapısı

**Silinecekler:**
- `unity/` (tüm klasör, ~3,9 MB, 22 `.cs`)
- `python/net/osc_sender.py`, `tools/osc_sniff.py`
- `requirements.txt` → `python-osc` satırı
- `python/config.json` → `osc` bloğu; `net.transport` alanı (tek taşıyıcı WS
  kaldı, seçim anlamsız)
- `python/net/__init__.py` → `create_sender` yalnız `WsSender` döner,
  `CompositeSender` gider
- `README.md` (kök) **yeniden yazılacak** — bugün hâlâ Unity/OscJack mimarisini
  anlatıyor, `KIOSK.md` ile çelişiyor

> ⚠ **`unity/` içinde MathLens dışında `CheeseHunt.unity` ve `MouseTrap.unity`
> sahneleri + script'leri var — iki ayrı sergi oyunu.** Silinince onlar da
> aktif ağaçtan gider. Git geçmişinde durmaya devam ederler; kurtarma noktası
> **`b41f122`** olarak `README.md`'ye ve silme commit'inin mesajına yazılacak.
> Kullanıcı "hiçbir bağı kalmamış olmalı" dedi, bu yüzden silme yapılıyor —
> ama bu satır kaybın bilinçli olduğunu kayda geçirir.

**Kurulacak:** `pytest.ini` + `tests/` (SprayTarih'in `pytest.ini`'si desen).
Bu noktada tek test bile yeşilse yeter — sonraki her görev RED→GREEN buraya
yazacak.

---

## G2 — `paths.py` + tek giriş noktası `matematik.py`

İki temel taş. **Lisans hattının tamamı bunlara dayanır.**

### `paths.py` (kök) — SprayTarih `backend/paths.py` deseni

```
FROZEN            = "__compiled__" in globals() or sys.frozen
resource_root()   # salt okunur: web.pak, lisans_web/, models/*.task
data_root()       # yazılabilir: %LOCALAPPDATA%\MatematikAvi (donmuş) | depo kökü (kaynak)
VERI_DOSYALARI    = ("config.json", "calib.json", "aktivasyon.dat")
ensure_seeded()   # config.json tohumlanır; calib.json ve aktivasyon.dat TOHUMLANMAZ
```

- `calib.json` **tohumlanmaz** — başka salonun kalibrasyonu bu makinede yanlış.
- `aktivasyon.dat` **tohumlanmaz** (§3.4) — makineye özel, HMAC'i de tutmaz.
- `config.json` tohumlanır (kamera indeksi gibi ayarlar için varsayılan gerek).
- **Mutlak sürücü yolu yok** — her şey `Path(__file__)`'dan (kök `CLAUDE.md`).

### `matematik.py` (kök) — `start-kiosk.ps1`'in Python karşılığı

SprayTarih `spray.py` (323 satır) birebir şablon. Yaptığı iş:

```
LİSANS KAPISI (kamera/port'tan ÖNCE)  →  web.pak çöz  →  paths.ensure_seeded()
  →  statik sunucu (bellekten)  →  WS portu seç  →  dedektör thread'i
  →  Chrome --app --start-fullscreen
```

Yeniden kullanılacak SprayTarih yordamları: `_free_port`, `_wait_for_port`,
`_open_browser` (`spray.py:100-135`), `_fatal` (ctypes MessageBox — konsolsuz
EXE'de açılış hatası aksi halde hiçbir yerde görünmez), `LisansReddedildi`.

**sys.path wrinkle:** `python/` bir paket değil, modülleri birbirini düz
isimle import ediyor (`from config import load_config`). `matematik.py` kök ve
`python/` dizinlerinin ikisini de `sys.path`'e ekler; `python/main.py`'ye de
kökü ekleyen 3 satırlık bir bootstrap girer ki `cd python && python main.py`
bozulmasın. Nuitka tarafında her modül `--include-module=` ile sayılır.

`Matematik-Avi-Baslat.bat` artık `python matematik.py` çağırır;
`start-kiosk.ps1` silinir (işi `matematik.py` devraldı).

---

## G3 — Lisans Merkezi'nde ürünü aç + lisans çekirdeği (plan §2, §3)

1. `LisansMerkezi/urunler.py` → `matematik.klasor` **zaten doğru**
   (`Matematik_Avi`). `etkin` **`False` kalır** (G10'a kadar).
2. **Anahtar çifti üret — GERİ ALINAMAZ:** `MERKEZ.bat` → Matematik Avı →
   kurulum kartı → "Anahtar çifti üret". Ekrandaki **64 haneli açık anahtarı
   kaydet**. Hemen **depo yedeği** al (üst çubuk).
3. `python -c "import urunler; urunler.kopyayi_guncelle('matematik')"` →
   `Matematik_Avi/lisans_bicim.py`. **Elle düzenlenmez**
   (`LisansMerkezi/tests/test_urunler.py` SHA-256 ile denetler).
4. Kökte dört dosya (SprayTarih'ten port, sabitler değişir):
   - `lisans.py` — `URUN="matematik"`, `PAKET_NO=1`, `ACIK_ANAHTAR_HEX=<2. adım>`
   - `lisans_durum.py` — `data_root()/aktivasyon.dat`, HMAC yalnız birincil
     bileşenden (PBKDF2-SHA256 100k), saat geri-alma hoşgörüsü 86 400 sn
   - `parmak_izi.py` — 3 bileşenden 2'si; `_bilesenleri_topla()` enjeksiyon
     noktası, testler asla WMI çağırmaz

**Testler (RED önce):** `tests/test_lisans.py`, `test_lisans_durum.py`,
`test_parmak_izi.py` — SprayTarih'te sırasıyla 12 / 13 / 9 test var, aynı
kapsam hedeflenir. Hepsi donanımsız koşar.

---

## G4 — İçerik paketi + offline fontlar + bellekten servis (plan §4)

### `web_paket.py` — SprayTarih'ten port, **tek fark başlık**

```
MAPAK1\n | paket_no (4 bayt BE) | 12 bayt nonce | AES-256-GCM(zip(web/))
```

`paketle(kok, anahtar, paket_no)`, `coz(veri, anahtar) -> dict`,
`paket_no_oku(veri)`. Anahtar bu modülde **yok** — çağıran onu lisansın imzalı
yükünden getirir.

### Fontları yerele al (yeni iş, SprayTarih'te karşılığı yok)

Baloo 2 / JetBrains Mono / Space Grotesk `.woff2`'leri `web/fonts/` altına
indir, `web/index.html:7-9` CDN `<link>`'lerini sil, `web/styles.css` başına
`@font-face` blokları ekle. Üçü de SIL Open Font License — gömülmesi serbest.
Türkçe (`İ ı ğ Ğ ş Ş ç Ç ö ü`) + matematik (`× ÷ √ ² −`) glyph kapsaması
göç planı §10.5'te zaten şart koşulmuş; latin-ext alt kümesi alınacak.
Fontlar `web/` altında olduğu için otomatik olarak `web.pak`'e girer.

### Statik sunucu bellekten servis etsin

`tools/serve.py` (SprayTarih `tools/serve.py:81-96` port) —
**`yol_coz(istek)` sorgu dizisini ve `#`'i ATMALI.** `index.html:147-153`
script'leri `?v=4` ekiyle çağırıyor; atılmazsa `/js/game.js?v=6` 404 döner ve
oyun boş ekran açar. Testle kilitlenir.

MIME tablosu **elle yazılır** — donmuş ortamda `mimetypes` eksik gelir,
Windows registry `.js`'i `text/plain` döndürebilir.

**Testler:** `tests/test_web_paket.py` (~6), `tests/test_serve.py` (~11,
içinde sorgu dizisi ve `..` güvenlik testleri).

---

## G5 — Lisans ekranı (plan §5)

- `lisans_web/index.html` — **pakete ham girer**, `web.pak`'in dışında.
  Şifreli pakete girseydi lisans olmadan açılamazdı.
- `lisans_ekrani.py` (SprayTarih 142 satır port):
  - `durumu_belirle(kayit, izi, simdi=None) -> (str, dict|None)` — **saf**;
    pencere açmaz, dosya yazmaz. **Makine bağı süreden ÖNCE** bakılır.
  - `aktive_et(metin)` — dosya seçme ve metin yapıştırma tek yola iner.
  - `ac(mesaj)` — `webview.create_window(html=...)`; **HTTP sunucusu hiç
    başlatılmaz** (o zaten şifreli paketi servis ediyor, elde anahtar yok).
- Yedi durum, yedi ayrı metin: `yok, doldu, baska_makine, saat, gecersiz,
  surum, urun`. `urun` metni: "Bu anahtar Matematik Avı için değil; başka bir
  oyunun anahtarı."
- `requirements.txt` → `pywebview` eklenir.

**Test:** `tests/test_lisans_ekrani.py` (~12), hepsi `durumu_belirle` üzerinden
— GUI açan tek test yok.

---

## G6 — Açılış kapısı + filigran (plan §6)

`matematik.py` içinde `lisans_kapisi(donmus: bool) -> bytes | None`
(SprayTarih `spray.py:180-222` deseni):

- `donmus=False` → **`None`, kapı yok.** Geliştirme döngüsü bozulmaz.
- `donmus=True` → `parmak_izi.al()` → `lisans_durum.oku()` →
  `durumu_belirle()`; geçerli değilse ekran açılır; hâlâ yük yoksa
  `LisansReddedildi(SystemExit)`.
- Çağrı yeri: `_main()`'in **en başı** — `ensure_seeded()`, statik sunucu,
  kamera, WS portu, Chrome hepsinden önce.

**Sıra testi** (`inspect.getsource(matematik._main)` içinde konum
karşılaştırması) — `tests/test_lisans_kapisi.py` (~14).

**Filigran (§6.4):** yalnız `tip == "demo"` iken; kalıcı lisansta **boş**.
İçerik `Kurum — GG.AA.YYYY — #anahtar_no`. Taşıma yolu **SprayTarih deseni:
`GET /filigran.json`** — WS protokolüne dokunulmaz (o `{x,y,present,gesture}`
sözleşmesi `ws_sender.py` docstring'inde sabit ilan edilmiş). `game.js`
açılışta bir kez okur.

---

## G7 — `Ctrl` ile masaüstü modu (plan §10'un yerine geçen sapma)

`web/js/input.js` bugün `?input=mouse|ws` ile **açılışta** seçiyor ve iki
sürücü de yazılı (satır 20-31 mouse, 34-70 ws). Değişiklik:

- Her iki sürücü de **kurulur**, ama paylaşılan `hand` nesnesine yalnız aktif
  olan yazar. `MA.input.driver` ("ws" | "mouse") ve `MA.input.setDriver(ad)`.
- `keydown` → `e.key === "Control" && !e.repeat` → toggle. `Escape` dışında
  bağlı tuş yok, çakışma yok (§10.2 TUZAĞI kontrol edildi).
- Toggle olunca ekranda küçük, kalıcı bir rozet: "FARE MODU". Aksi halde
  operatör yanlışlıkla bastığında sergi sessizce ölür.
- Oyun mantığı hangi sürücüden beslendiğini **bilmez** — `game.js`/`lens.js`
  yalnız `MA.input.hand` okur. Mevcut seam korunur, dokunulmaz.
- `?input=` parametresi **açılış varsayılanı** olarak kalır: `matematik.py`
  donmuş ortamda `?input=ws` verir; kaynaktan geliştirmede `mouse` varsayılan.

Dedektör her iki modda da çalışmaya devam eder (kamera açılır); fare modunda
gelen kareler sessizce yoksayılır. Bu bilinçli: kullanıcı geçici bir devir
istedi, kalıcı bir kurulum tercihi değil.

**Doğrulama elle:** Ctrl → lens fareyi izler, rozet görünür; Ctrl → el takibi
geri döner, rozet kaybolur. Basılı tutmak tek toggle üretir (`e.repeat`).

---

## G8 — `surum.py` + `build.py` (plan §7, §8)

### `surum.py` — sürümün tek kaynağı

```python
SURUM = "0.9.0"
URUN_ADI = "Matematik Avi"      # ASCII: Windows kaynak tablosu + ISCC cp1254
SIRKET = "Luden Studio"
DOSYA_SURUMU = SURUM + ".0"
KURUCU_ADI = f"MatematikAvi-Setup-{SURUM}-win64"
```

0.9.x kendi test kurulumların; **ilk müşteri teslimi 1.0.0**.

### `build.py` — SprayTarih `tools/build_exe.py` (554 satır) port

- **Nuitka standalone** (onefile değil) — mediapipe/cv2 veri dosyaları yüzünden.
  G0'ın devir notu hangi bayrakların gerçekten gerektiğini söyler.
- `--include-data-files=dist/web.pak=web.pak`
- `--include-data-dir=lisans_web=lisans_web` (**ham**)
- `--include-data-files=python/models/hand_landmarker.task=models/hand_landmarker.task`
  — model yoksa build **durur** (Aican'ın Whisper kararı; aksi halde sergi ilk
  açılışta indirmeye çalışır ve ağ yoksa sessiz kalır)
- **`web/` ham ağacı GÖMÜLMEZ** — o satır varsa tüm şifreleme anlamsız
- `--include-module=lisans,lisans_bicim,lisans_durum,lisans_ekrani,parmak_izi,web_paket,surum,paths`
  `--include-package=cryptography`, `--include-package-data=mediapipe,cv2`
- Damga bayrakları altısı da `surum.py`'den
- **İçerik anahtarı ÜRETİLMEZ, OKUNUR:** `LUDEN_LISANS` env ya da
  `~/.luden-lisans/urunler/matematik/icerik.key`
- **JS obfuscation (§7.2)** muhafazakâr: `--rename-globals false`,
  `--control-flow-flattening false`, `--compact/--string-array true`;
  `web/fonts/` dışarıda; node yoksa build durmasın diye `--obfuscate-yok`
- `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` + satır başına
  `try/except UnicodeEncodeError`

### `.gitignore` (Matematik_Avi kökü)

`.luden-lisans/`, `*.key`, `lisans.dat`, `lisanslar.json`, `dist/web.pak`,
`dist/web-hazir/`, `dist/`

**Test:** `tests/test_build.py` (~20) — bayrak varlığı, `surum.py`'den
geldikleri, ham `web/` ağacının gömülmediği.

---

## G9 — Kurucu (plan §9)

- `installer/MatematikAvi.iss` — **yeni GUID** (`AppId`), `AppVersion={#SURUM}`
  ve `OutputBaseFilename={#KURUCU_ADI}` **elle yazılmaz**, `/DSURUM=` ile
  geçer. `DefaultDirName={autopf}\Luden Studio\Matematik Avi`,
  `PrivilegesRequired=admin`, `ArchitecturesAllowed=x64compatible`,
  `Compression=lzma2/max`, Türkçe `compiler:Languages\Turkish.isl`.
- **ISCC arama (§9.1 TUZAK):** adaylar `LOCALAPPDATA`, `ProgramFiles(x86)`,
  `ProgramFiles` ortam değişkenlerinden türetilir; `ISCC` env hepsini ezer.
  Sürücü harfi hardcode edilmez. winget derleyiciyi `%LOCALAPPDATA%\Programs\
  Inno Setup 6\ISCC.exe` altına koyuyor.
- **Standalone olduğu için "[Files] tek satır" kuralı uygulanamaz** —
  SprayTarih'teki çözüm alınır: ISCC'den **önce** `dist/` taranır, yasak ad
  listesi (`aktivasyon.dat`, `calib.json`, `config.json`, `*.key`,
  `lisanslar.json`, ham `web/`) bulunursa build **durur**.
  `dist/veri/aktivasyon.dat` tek başına lisans kapısını açar; kurucuya girerse
  dağıtılan her kopya sistemi bypass eder.
- `build.py --kurucu` akışı: EXE var mı → dist taraması → ISCC → kurucu →
  **ZIP** (tarayıcı/e-posta çıplak `.exe` engelliyor) → **SHA-256 yazdır**.
  ZIP'in içine `KURULUM.txt` de girer.

**Test:** `tests/test_kurucu.py` (~17) — SprayTarih'teki denetimlerin aynısı.
Kırmızıysa **paket gönderilmez**.

---

## G10 — Teslim belgeleri + kapanış (plan §11, §14)

- `docs/KURULUM.md` (müşteri): SmartScreen adımında **"Daha fazla bilgi"** ve
  **"Yine de çalıştır"** ifadeleri birebir geçmeli (testle kilitlenir — destek
  çağrılarının en yaygın sebebi). Anahtar girme, **Ctrl fare modu**,
  kalibrasyon, hata mesajları tablosu, SSS.
- `docs/TESLIM.md` (kendi kontrol listen): temiz build, `pytest
  tests/test_kurucu.py`, Merkez'den anahtar, e-postada dört şey.
- `README.md` (kök) — Unity mimarisini anlatan metin yeniden yazılır;
  "Lisans", "Kurucu", "Kalibrasyon", "Ctrl fare modu" bölümleri + §15'in
  **dürüst sınırları**.
- `LisansMerkezi/urunler.py` → `matematik` **`etkin: True`**;
  `LisansMerkezi/tests/test_urunler.py:30` (`"matematik" not in etkin_kodlar()`)
  ve `test_koprusu.py:30` bu satırla birlikte güncellenir.
- Repo kökü `CLAUDE.md` → Matematik Avı satırına lisans hattı notu, SprayTarih
  ve Aican notlarının desenine uygun.

---

## Doğrulama

### Her görev sonunda

```
pytest                     # taban test sayısı KIRILMADAN yeşil
git status --short | grep -iE "\.key|lisanslar\.json|luden-lisans|web\.pak|aktivasyon"
                           # BOŞ çıkmalı
```

### Build sonrası (plan §13)

| # | Kontrol | Beklenen |
|---|---|---|
| 1 | Merkez'den üretilen key `lisans.dogrula()`'da | ürün/kurum/süre okunur |
| 2 | O key'in içerik anahtarı `web_paket.coz()`'de | dosya listesi çıkar |
| 3 | EXE lisanssız | lisans ekranı açılır, oyun açılmaz |
| 4 | `dist/` altında ham `web/` klasörü | **yok** |
| 5 | EXE/dist içinde `questions.js` soru metinleri düz olarak | **yok** |
| 6 | Aktivasyondan sonra | oyun açılır, `/js/game.js?v=6` **200**, olmayan yol 404 |
| 7 | **İnternetsiz açılış** | fontlar doğru (tofu yok), model yükleniyor |
| 8 | Kaynaktan çalıştırma | değişmemiş, lisans hiç sorulmaz |
| 9 | Ctrl | fare modu açılır/kapanır, rozet doğru |

### Kurucu sonrası

ZIP içeriği yalnız kurucu + `KURULUM.txt`; `(Get-Item ...exe).VersionInfo`
dolu; Program Files'a kurulup açılınca lisans ekranı; anahtar sonrası
`%LOCALAPPDATA%\MatematikAvi\aktivasyon.dat` oluşur; kaldır→kur sonrası
`calib.json` yerinde.

> **`dist\...exe`'yi doğrudan çalıştırarak test etme** — yanındaki aktivasyon
> senin geçerli aktivasyonundur, lisans ekranı hiç çıkmaz. Temiz test
> kurucudan geçer.

### Süre testi

Merkez'de **1 dk (TEST)** anahtarı — süre üretimden sayılır, havuza konmaz,
müşteriye verilmez.

### Elle (kullanıcıya bırakılır)

Temiz Windows + internet kapalı; saati 5 gün geri al → "Sistem saati geri
alınmış görünüyor."; kurulum klasörünü ikinci makineye kopyala → "Bu kurulum
başka bir bilgisayara ait."

---

## Riskler / açık uçlar

1. **mediapipe + Nuitka** — G0'ın cevaplayacağı tek şey. Kırmızı gelirse
   çözüm yolu: modeli ve mediapipe veri ağacını `--include-package-data` yerine
   elle `--include-data-dir` ile taşımak; son çare onefile yerine yanına kopya.
2. **dist boyutu.** mediapipe + opencv ile SprayTarih ölçeğinde (yüzlerce MB)
   beklenir; Aican'ın 4 GB'ı burada söz konusu değil (LLM yok).
3. **Submodule sahipliği:** `Matematik_Avi` remote'u
   `atlamayanat/Matematik_Avi` — kökün `eemresari/v1-kasa`'sından **farklı bir
   hesap**. Push gerekirse yetki teyidi lazım (push zaten kullanıcı onaylı).
4. **Çalışma ağacı temiz değil:** `python/camera/webcam.py`, `python/config.json`,
   `python/main.py` değişmiş durumda. İşe başlamadan bunlar gözden geçirilip
   commit'lenmeli, yoksa G1'in temizliğiyle karışır.
5. **`unity/` silinince CheeseHunt + MouseTrap kaynakları aktif ağaçtan gider**
   (yukarıda G1'de işaretlendi; kurtarma noktası `b41f122`).
6. **`styles.css` hâlâ `cqmin` kullanıyor** (göç planı `vmin` istiyordu). Bu
   hattın işi değil; dokunulmayacak, ama font değişikliği sırasında fark
   edilirse ayrı bir not olarak kaydedilir.
