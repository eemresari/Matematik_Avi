# G0 — Nuitka build spike devir notu (2026-09-12)

Plan: `docs/plans/2026-09-12-lisans-ve-kurucu-entegrasyonu.md` → G0.

**Soru:** mediapipe + opencv + websockets bağımlılıklarıyla `python/main.py`
Nuitka **standalone** olarak derlenip, çıkan EXE kamerayı açıp `.task` modelini
yükleyebiliyor mu?

**Cevap: EVET — ama planda olmayan İKİ bayrak zorunlu.** Derleme sorunsuz;
donmuş EXE kamerayı açıyor, modeli yüklüyor, 30 fps inference yapıyor ve
WebSocket köprüsünden kare gönderiyor. **Uçtan uca doğrulandı.**

İki tuzak da **aynı şekle** sahip: kütüphane kendi alt modülünü çalışma anında
(ctypes / lazy_import) yüklüyor, Nuitka statik analizde göremiyor, **derleme
yeşil çıkıyor ama EXE bozuk oluyor.** Bu sınıf hatayı derleme çıktısı
yakalamaz — yalnız EXE'yi gerçekten çalıştırmak yakalar.

---

## Ortam

Matematik Avı'nın kendi venv'i yoktu; kuruldu (`.venv/`, `.gitignore`'da zaten
dışlanmış). KimyaLab/aican'daki kanıtlı bileşim örnek alındı:

| Bileşen | Sürüm | Not |
|---|---|---|
| Python | 3.12.10 | KimyaLab/aican venv'leriyle aynı |
| Nuitka | 4.2.1 | KimyaLab/aican'da 4.2 |
| mediapipe | 0.10.35 | depo `requirements.txt`'inde sabit |
| opencv-python | **5.0.0** | 4.11 de ölçüldü — aşağıya bak |
| numpy | **2.5.3** | cv2 5 yükseltmesi beraberinde getirdi |
| websockets | 16.1.1 | SprayTarih `<17` pinliyor |

> **opencv: İKİ yığın da ölçüldü, ikisi de yeşil. Pin GEREKMİYOR.**
> Spike önce 4.11 + numpy 1.26 (SprayTarih deseni) ile kuruldu ki G0'ın sorusu
> "mediapipe + Nuitka" olarak kalsın. Sonra kullanıcı kararıyla depo'nun
> tavansız `>=4.9`'unun bugün ürettiği yığın da ölçüldü:
>
> | Yığın | Derleme | Donmuş EXE | Boyut |
> |---|---|---|---|
> | cv2 4.11 + numpy 1.26 | ✅ | ✅ model + inference | 306 MB / 280 dosya |
> | **cv2 5.0.0 + numpy 2.5.3** | ✅ | ✅ kamera + inference + WS | **280 MB / 264 dosya** |
>
> cv2 5 yığını **26 MB daha küçük** ve makinedeki global ortamla (oyunun bugün
> çalıştığı sürümlerle) **birebir aynı**. `opencv-python>=5`'e yükseltmek
> numpy'yi de 2.5.3'e çekiyor — iki değişken birden değişti, ama sonuç yeşil
> olduğu için ayrıştırmaya gerek kalmadı. G8 `requirements.txt`'e tavan
> **koymayabilir**; SprayTarih'in `<5` pini buraya taşınmak zorunda değil.

---

## Sonuç

| Adım | Durum |
|---|---|
| Nuitka standalone derleme | **GEÇTİ** — exit 0, **~3 dk** |
| dist boyutu | **280 MB / 264 dosya** (cv2 5 + numpy 2 ile) |
| EXE açılış + `config.json` okuma | **GEÇTİ** |
| Gömülü `.task` modelini yükleme | **GEÇTİ** (DLL bayrağından sonra) |
| HandLandmarker **LIVE_STREAM** inference | **GEÇTİ** — callback döndü |
| **Kamera açma (donmuş EXE)** | **GEÇTİ** — `640x360`, **cam 30 fps** |
| **Inference hızı (donmuş EXE)** | **GEÇTİ** — **infer 30 fps** |
| **WebSocket köprüsü** | **GEÇTİ** (websockets bayrağından sonra) |
| **Uçtan uca `ws_sniff`** | **GEÇTİ** — 6 sn'de **180 kare** (30 Hz) |

`ws_sniff` örnek karesi — `ws_sender.py` docstring'indeki sözleşme birebir:
`{'x': 0.5, 'y': 0.5, 'present': False, 'gesture': 'open'}`
(`present=False` doğru: kameranın önünde el yoktu.)

> **Kamera fourcc notu:** kamera **MJPG değil YUY2** negotiate etti
> (`[camera] index=0 negotiated 640x360 fourcc=YUY2`). Bu, `python/camera/webcam.py`
> içindeki MJPG yorumunun yazıldığı senaryonun tam kendisi; native 640x360'ta
> 30 fps tuttuğu için o düzeltme **gerçek donanımda doğrulanmış** oldu.

---

## Zorunlu bayrak 1 (planda YOK) — mediapipe

```
--include-data-files=<site-packages>/mediapipe/tasks/c/libmediapipe.dll=mediapipe/tasks/c/libmediapipe.dll
```

**Neden:** mediapipe **0.10.35**'te tasks motoru bir Python uzantısı (`.pyd`)
değil, **ctypes ile yüklenen bir C kütüphanesi**: `tasks/c/libmediapipe.dll`
(28,7 MB) — paketin içindeki **tek** ikili dosya, `.pyd` hiç yok.

İki şey birden ıskalıyor:
1. **ctypes çağrısı statik analize görünmez** — Nuitka import zincirini takip
    ederken göremez.
2. **`--include-package-data=mediapipe` `.dll` almaz** — yalnız 5 adet
    `.txt`/`.fbs` kopyalandı; dist'te mediapipe'a ait **hiç ikili yoktu**.

Bayraksız belirti (derleme yeşil, hata **çalışma anında**):

```
FileNotFoundError: Could not find module '...\mediapipe\tasks\c\libmediapipe.dll'
  mediapipe_c_bindings.py: load_shared_library -> ctypes
```

`HandLandmarker.create_from_options()` çağrısında patlar — yani `import
mediapipe` **başarılı olur**, hata ilk gerçek kullanımda çıkar. Kamera hatasının
arkasına saklanmıştı; kamerasız bir probe EXE derlenerek açığa çıkarıldı.

**Yol hardcode edilmez** — paketin konumundan türetilir (kök `CLAUDE.md`):

```python
import mediapipe
dll = Path(mediapipe.__file__).parent / "tasks" / "c" / "libmediapipe.dll"
```

> **SprayTarih deseni neden yetmedi:** SprayTarih `mediapipe>=0.10.9,<0.11`
> pinliyor ve muhtemelen C bindings'ten **önceki** bir 0.10.x ile derlendi.
> `--include-package-data=mediapipe` orada yeterliydi; 0.10.35'te değil.

---

## Zorunlu bayrak 2 (planda YOK) — websockets

```
--include-package=websockets
```

**Bu ikisinin en sinsisi.** `ws_sender.py:57` düz `websockets.serve(...)`
çağırıyor. websockets **14+** kendi alt paketlerini `lazy_import` ile çözüyor
(`websockets/__init__.py:139`), yani `serve` çalışma anında
`websockets.asyncio.server`'ı import ediyor. Nuitka yalnızca `import websockets`
görüyor, `websockets.asyncio`'yu **hiç** görmüyor.

Bayraksız belirti — **traceback YOK, çıkış kodu 0, EXE çalışmaya devam ediyor:**

```
[camera] index=0 negotiated 640x360 fourcc=YUY2      <- kamera calisiyor
[ws] ERROR: server failed to start (0.0.0.0:8765): No module named 'websockets.asyncio'
[detector] running. transport=ws                      <- "calisiyorum" diyor
[stat] cam 30.0 fps  infer 30.0 fps  hands 0          <- inference de calisiyor
```

Dedektör mutlu görünüyor, kamera 30 fps dönüyor, ama **port hiç açılmıyor** ve
**tarayıcı tek kare almıyor → oyun boş ekran.** Sergi kurulumunda bunu yakalayan
tek şey, kimsenin okumadığı logdaki o tek `ERROR` satırıdır.

`--include-module=net.ws_sender` bunu **çözmez** — o proje modülünü getirir,
`websockets`'in kendi alt paketini değil.

> **G8 TESTİ ZORUNLU:** `tests/test_build.py` bu bayrağın varlığını kilitlemeli.
> Sessiz bozulan bir özelliğin regresyonu, gürültülü çökenden daha pahalıdır.

---

## Denendi, OLMADI: `--nofollow-import-to=matplotlib`

Cazip görünüyordu — paket **306 → 245 MB**, **280 → 70 dosya**. Ama EXE
**import anında** ölüyor:

```
mediapipe.tasks.python.vision.__init__
  -> drawing_styles -> drawing_utils -> import matplotlib
ImportError: Module 'matplotlib' was actively excluded from Nuitka compilation.
```

**tasks API'nin kendisi** matplotlib çekiyor (biz `solutions` kullanmasak bile).
matplotlib + Tk/Tcl + PIL (~30 MB) **zorunlu yüktür**. G8'de tekrar denenmesin.

---

## Kullanılan tam bayrak kümesi (çalışan hali)

```
--assume-yes-for-downloads
--standalone                       # onefile DEĞİL (mediapipe/cv2 veri dosyaları)
--windows-console-mode=force       # spike'ta; ürün EXE'sinde disable olacak
--enable-plugin=no-qt              # Qt yığınını engeller (Tk yine de gelir)
--include-package-data=mediapipe   # gerekli ama TEK BAŞINA YETMEZ (yukarı bak)
--include-package-data=cv2
--include-data-files=<mp>/tasks/c/libmediapipe.dll=mediapipe/tasks/c/libmediapipe.dll
--include-module=net.ws_sender     # net/__init__.py bunları FONKSİYON İÇİNDE
--include-module=net.osc_sender    #   (tembel) import ediyor
--include-package=websockets       # ZORUNLU — lazy_import; yoksa köprü SESSİZ ölür
--include-data-files=python/models/hand_landmarker.task=models/hand_landmarker.task
--include-data-files=python/config.json=config.json
```

`--enable-plugin=no-qt` işe yaradı (dist'te Qt yok) ama **Tk kaldı**
(`_tkinter.pyd`, `tcl86t.dll`, `tk86t.dll`) — matplotlib'in Tk arka ucu.

**cp1254 tuzağı gerçek:** spike script'inin ilk işi
`sys.stdout.reconfigure(encoding="utf-8", errors="replace")`. Plan §9.6 haklı.

---

## Boyut dökümü (280 MB — cv2 5 yığını)

| Bileşen | MB | Not |
|---|---|---|
| `cv2` | **112** | tek başına paketin ~%40'ı |
| `main.exe` | 53 | Nuitka derlenmiş modülleri gömüyor |
| `mediapipe` | 28 | neredeyse tamamı `libmediapipe.dll` |
| `numpy.libs` | 21 | OpenBLAS (cv2 4.11/numpy 1.26'da 37 MB'dı) |
| `matplotlib` + Tk/Tcl + PIL | ~25 | atılamıyor |
| `models/` | 8 | `hand_landmarker.task` |

**G8 için aday kısıntı (DENENMEDİ):** `cv2/opencv_videoio_ffmpeg500_64.dll`
**31 MB** — paketin ~%11'i — ve yalnız dosyadan video okumak/yazmak için
gerekir; webcam yakalama DSHOW/MSMF üzerinden gider. Atılabilir görünüyor.
Ölçülmedi çünkü G0'ın sorusu değildi; G8'de denenirse **EXE çalıştırılarak**
doğrulanmalı (bu spike'ın ana dersi).

`opencv-python-headless` **uygun değil**: kalibrasyon sihirbazı cv2 GUI
pencereleri açıyor. Kurucu
(lzma2/max) bu 280 MB'ı ciddi sıkıştırır — SprayTarih ölçeğinde beklenir.

Aican'ın 4 GB'ı burada söz konusu değil; plan §riskler-2 doğru çıktı.

---

## Kamera testi — YAPILDI (kamera takıldı)

İlk derlemeler kamerasız bir makinede koştu; EXE `camera/webcam.py:23`'te
`RuntimeError: Could not open webcam at device_index=0` ile duruyordu. Bu
**paketleme hatası değildi** — kaynaktan da aynısı oluyordu (DSHOW 0/1/2
indekslerinin hiçbirini açamıyor). Kamera takıldıktan sonra donmuş EXE:

```
[camera] index=0 negotiated 640x360 fourcc=YUY2 (requested 640x360 MJPG)
[ws] WebSocket bridge -> ws://0.0.0.0:8765
[detector] running. transport=ws  calibrated=False
[stat] cam 30.0 fps  infer 30.0 fps  hands 0
```

`ws_sniff`: 6 sn'de **180 kare** (30 Hz), sözleşme doğru.

> **Kamerasız makinede spike koşulmasının bir yararı oldu:** kamera hatası
> mediapipe DLL eksiğini maskeliyordu. Kamerasız bir `spike_probe.py` derlenerek
> o hata ortaya çıkarıldı. Kamera erken takılsaydı DLL sorunu da, websockets
> sorunu da G8'e sarkabilirdi.

### Doğrulanmayan tek şey: `present=True` yolu

Testte kameranın önünde el yoktu (`hands 0`, `present False`). El takibinin
**tespit** tarafı (HandLandmarker inference) 30 fps çalıştığı kanıtlandı, ama
bir elin gerçekten kilitlenip `present=True` + `gesture=fist` üretmesi
görülmedi. Bu **paketleme değil oyun mantığı** katmanı ve kaynakta çalıştığı
biliniyor; G6/G7 elle doğrulamasında zaten görülecek. Risk düşük.

---

## G8'e taşınacaklar

1. `libmediapipe.dll` bayrağı **zorunlu** — testle kilitlenmeli
   (`tests/test_build.py`, plan G8 ~20 test): bayrak var mı **ve** yol
   mediapipe paketinden türetiliyor mu (hardcode değil).
2. `--include-package=websockets` **zorunlu** — testle kilitlenmeli. Sessiz
   bozulduğu için en kritik test bu.
3. `--nofollow-import-to=matplotlib` **yasak** — sebebi yorum olarak kalsın.
4. opencv pini **gerekmiyor** (ikisi de ölçüldü, yukarı bak).
5. `--windows-console-mode`: spike'ta `force`, üründe `disable`
   (SprayTarih deseni; konsolsuz EXE'de açılış hatası görünmez → `_fatal`
   ctypes MessageBox şart, plan G2 zaten istiyor).
6. Model yoksa build **dursun** (plan G8, Aican'ın Whisper kararı).
7. **Derleme yeşilliği kanıt değildir.** İki bayrak da derlemeyi geçti, EXE'yi
   geçemedi. G8'in "build başarılı" tanımı EXE'yi **çalıştırıp** köprüden kare
   okumayı içermeli; yoksa aynı sınıf hata bir kütüphane yükseltmesinde geri
   gelir ve sergide sessizce ortaya çıkar.

## Spike artıkları (COMMIT EDİLMEZ)

`spike_build.py`, `spike_probe.py`, `build-spike/` — G0 kapanınca silinir.
`.venv/` kalır (`.gitignore`'da). `.gitignore`'a `build-spike/` eklenmedi;
silinecekleri için gerek görülmedi — **commit öncesi `git status` kontrol et.**
