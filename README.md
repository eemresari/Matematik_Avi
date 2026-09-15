# Matematik Avı — El Hareketiyle Matematik Sergisi

İnteraktif sergi: bir web kamerası kullanıcının elini izler; duvara yansıtılan
**tarayıcı tabanlı** oyunda mercek elin konumunu takip eder, doğru sayı
tuzağını yumrukla yakalayınca skor artar. Oyun mantığının tamamı (soru
havuzu, tuzak üretimi, tur akışı, skor tablosu) **web/js** içindedir; Python
yalnızca görü katmanıdır.

> **2026-09-15 güncellemesi:** proje tamamen web'e göçtü. Eski Unity/OSC
> mimarisi (`unity/`, `python/net/osc_sender.py`) kaldırıldı; o ağaçta
> `MathLens`'in yanında iki ayrı sergi oyunu da vardı (`CheeseHunt.unity`,
> `MouseTrap.unity`) — ikisi de aktif ağaçtan gitti ama git geçmişinde
> `b41f122` commit'inde durmaya devam ediyor. Sergi/kiosk kurulumu için önce
> [KIOSK.md](KIOSK.md)'ye bakın.

## Mimari

```
  Webcam ─► [PYTHON: dedektör]                        [TARAYICI: oyun]
            MediaPipe HandLandmarker                   web/js/game.js
            → aktif oyuncu seçimi (lock-on)             + lens.js (mercek)
            → jest FSM (açık/yumruk)      WebSocket      + tokens.js (tuzaklar)
            → homografi (kamera→duvar)  ────/hand───►    + questions.js (sorular)
            → One Euro yumuşatma                         + leaderboard.js
```

- **İki süreç, tek mesaj:** Python görüyü yapar, tarayıcıya JSON bir kare
  gönderir → `{x, y, present, gesture}` (`python/net/ws_sender.py`).
- **Tarayıcı saf renderer değil, oyunun kendisi:** soru üretimi, tuzak
  yerleşimi, skor mantığı JS'te. Python'u yeniden derlemeden oyun mantığını
  değiştirebilirsin.
- **`matematik.py`** tek giriş noktası: statik sunucu + tarayıcı + dedektörü
  tek süreçte başlatır (eski `start-kiosk.ps1`'in yerini aldı).
- **Ctrl fare modu:** kamerasız bir demo makinesinde `Ctrl` tuşu fareyi el
  takibiyle değiştirir; ekranda "FARE MODU" rozeti görünür.

## Hızlı başlangıç (geliştirme)

```
cd python
pip install -r requirements.txt
python download_model.py
cd ..
python matematik.py --pencere
```

Kiosk/sergi kurulumu (tek makine, çift makine, otomatik başlatma, sorun
giderme) için: [KIOSK.md](KIOSK.md).

## Lisans + dağıtım

Ürün, Lisans Merkezi'nin genel şablonuyla (KimyaLab/SprayTarih/Aican ile aynı
desen) paketlenir: `web/` şifreli tek bir `web.pak`'e (AES-256-GCM) konur,
Nuitka ile makine koduna derlenir, Inno Setup ile tek bir kurucuya sarılır.

| Adım | Komut | Not |
|---|---|---|
| Standalone derleme | `python build.py` | `build/matematik.dist/` |
| Kurucu + ZIP + SHA-256 | `python build.py --kurucu` | `dist/MatematikAvi-Setup-<sürüm>-win64.zip` |
| Anahtar üretimi | `LisansMerkezi/MERKEZ.bat` | Matematik Avı → key ver |

- Oyunun içinde hiçbir özel anahtar yoktur; yalnız `lisans.ACIK_ANAHTAR_HEX`
  (açık anahtar) durur. EXE'yi parçalayan biri anahtar **üretemez**.
- Müşteriye giden belge: [docs/KURULUM.md](docs/KURULUM.md). Kendi teslim
  kontrol listen: [docs/TESLIM.md](docs/TESLIM.md).
- Entegrasyonun tam planı ve alınan kararlar:
  [docs/plans/2026-09-12-lisans-ve-kurucu-entegrasyonu.md](docs/plans/2026-09-12-lisans-ve-kurucu-entegrasyonu.md).

## Kalibrasyon

Projeksiyon + kamera yerleştirildikten sonra bir kez:
```
python matematik.py --kalibrasyon
```
(Kurulu EXE'de Başlat menüsündeki **Matematik Avı - Kalibrasyon** kısayolu
aynı işi görür.) 4 köşe yerine 3×3 = 9 hedef işaretlenir; `calib.json`'a
yazılır ve sonraki açılışlarda otomatik yüklenir. Detaylar: KIOSK.md §1.

## Kabul edilen sınırlar (§15, dürüst liste)

- Lisans **dosyasının** başka bir makinede yeniden aktive edilmesi
  engellenemez (çevrimdışı sistem); süre bunu bir tavanla sınırlar.
- `web.pak` lisanslı kullanıcı tarafından çözülebilir — korunan şey lisansı
  **olmayan** kişinin içeriği görememesi; JS obfuscation ek maliyet, mutlak
  engel değil.
- Kiosk sistem tarayıcısında (Chrome/Edge `--app=`) açılır; ikisi de yoksa
  varsayılan tarayıcıya düşer ve tam ekran için F11 gerekir.
- Ctrl fare modu kalıcı durum tutmaz: her açılış el takibiyle başlar; rozet
  hangi modda olunduğunu gösterir ama yanlışlıkla basılan Ctrl'ü engellemez.
- Anakart/disk değişince yeniden aktivasyon gerekir (HMAC birincil bileşenden
  türetilir).

## Klasör yapısı

```
Matematik_Avi/
├─ matematik.py            # Tek giris noktasi (lisans -> sunucu -> tarayici -> dedektor)
├─ paths.py                # Kaynak vs veri kokunun tek sahibi
├─ surum.py                # Surum/urun adi — tek kaynak
├─ build.py                # Nuitka standalone + kurucu + ZIP + SHA-256
├─ web_paket.py            # web/ -> tek sifreli AES-256-GCM paketi
├─ lisans.py, lisans_bicim.py, lisans_durum.py, lisans_ekrani.py, parmak_izi.py
├─ lisans_web/             # Lisans ekrani (pakete HAM girer)
├─ installer/MatematikAvi.iss
├─ web/                    # Oyunun TAMAMI: js/{game,lens,tokens,questions,...}.js
├─ python/                 # Gorü/algilama sureci
│  ├─ main.py              # Ana dongu (camera->detect->select->fsm->map->smooth->WS)
│  ├─ config.json          # Ayarlanabilir parametreler
│  ├─ camera/              # Kamera soyutlama (webcam | depth-stub)
│  ├─ detection/           # HandLandmarker sarmalayici
│  ├─ selection/           # Aktif oyuncu secimi + lock-on histerezisi
│  ├─ gesture/              # Jest debounce FSM
│  ├─ smoothing/           # One Euro filtresi
│  ├─ mapping/             # Homografi + 3x3 kalibrasyon
│  └─ net/                 # WebSocket gonderici (tek tasiyici)
├─ tools/                  # serve.py (bellekten servis), ws_sniff.py, kamera araclari
└─ tests/                  # pytest — donanimsiz, lisans/build/kurucu dahil
```
