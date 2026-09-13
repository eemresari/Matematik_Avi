"""Tek yerden yol çözümleme: paket içeriği (salt okunur) vs kullanıcı verisi (yazılabilir).

Bugün her modül yolunu çalışma dizinine göre buluyor: `main.py` `config.json`'ı
`--config` varsayılanıyla CWD'den, model ve `calib.json` da config'in içindeki
göreli yollardan okunuyor. Bu yüzden dedektör ancak `cd python` yapıldıktan
sonra çalışıyor. Tek giriş noktası (`matematik.py`) ve EXE bunu sürdüremez:

  * Paket içeriği (web.pak, lisans_web/, models/*.task) EXE'nin yanındadır ve
    **salt okunur** kabul edilir — Program Files'a kurulur.
  * Kullanıcı verisi (`config.json`, `calib.json`, `aktivasyon.dat`)
    `%LOCALAPPDATA%\\MatematikAvi` altındadır. Kalibrasyon sihirbazı ve lisans
    aktivasyonu bunlara **yazar**; Program Files'a yazamazlar.

Dondurulmuş bir build'de `__file__` çıkarma dizinini gösterir; oraya yazılan
kalibrasyon bir sonraki açılışta yok olur. Yolların tek sahibi bu dosyadır.
"""

import os
import shutil
import sys

# Nuitka derlenmiş her modüle `__compiled__` ekler; PyInstaller `sys.frozen` +
# `sys._MEIPASS` kullanır. İkisini de tanıyoruz ki derleyici değişirse yollar
# sessizce yanlış yere kaymasın.
FROZEN = ("__compiled__" in globals()) or getattr(sys, "frozen", False)

UYGULAMA_ADI = "MatematikAvi"

# Testlerin ve "taşınabilir kurulum" senaryosunun veri kökünü ezmesi için.
VERI_KOKU_ENV = "MATEMATIK_VERI_KOKU"

# Kurucuya ASLA girmemesi gereken dosya adları (G9 dist taraması bunu kullanır).
# `aktivasyon.dat` tek başına lisans kapısını açar; `calib.json` başka salonun
# kalibrasyonudur; `config.json` kurulum makinesinin kamera indeksini taşır.
VERI_DOSYALARI = ("config.json", "calib.json", "aktivasyon.dat")

MODEL_ADI = "hand_landmarker.task"

# Depo kökü: bu dosya kökte duruyor.
_KOK = os.path.dirname(os.path.abspath(__file__))


def resource_root() -> str:
    """Salt okunur paket içeriğinin kökü (web.pak, lisans_web/, models/)."""
    if FROZEN:
        meipass = getattr(sys, "_MEIPASS", None)      # PyInstaller onefile
        if meipass:
            return meipass
        return os.path.dirname(os.path.abspath(sys.executable))   # Nuitka standalone
    return _KOK


def data_root() -> str:
    """Yazılabilir kullanıcı durumunun kökü.

    KAYNAKTA `python/` — çünkü `config.json` ve `calib.json` bugün orada duruyor.
    (Plan "depo kökü" diyordu; `python/` seçildi ki `cd python && python main.py`
    akışı aynen çalışmaya devam etsin ve kökte ikinci, ayrışan bir `config.json`
    doğmasın. Tek dosya, tek gerçek.)
    """
    override = os.environ.get(VERI_KOKU_ENV)
    if override:
        return os.path.abspath(override)
    if FROZEN:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, UYGULAMA_ADI)
    return os.path.join(_KOK, "python")


def config_path() -> str:
    """Makineye özel `config.json` (kamera indeksi, eşikler)."""
    return os.path.join(data_root(), "config.json")


def ornek_config_path() -> str:
    """Tohumlama şablonu: donmuşta EXE'nin yanındaki kopya, kaynakta depodaki.

    Şablonun yeri veri kökünden BAĞIMSIZDIR. Veri kökü ezildiğinde (taşınabilir
    kurulum, testler) şablon yine depodaki `python/config.json`'dır; aksi halde
    şablon hedefin kendisi olur ve tohumlama sessizce hiçbir şey yapmaz.
    """
    kok = resource_root() if FROZEN else os.path.join(_KOK, "python")
    return os.path.join(kok, "config.json")


def calib_path(ad: str = "calib.json") -> str:
    """`calibration.file` mutlak değilse kullanıcı veri kökünde çözülür."""
    if os.path.isabs(ad):
        return ad
    return os.path.join(data_root(), ad)


def model_path(ad: str = MODEL_ADI) -> str:
    """MediaPipe el modeli. Donmuş build modeli GÖMÜLÜ taşır (internetsiz açılış)."""
    if os.path.isabs(ad):
        return ad
    kok = resource_root() if FROZEN else os.path.join(_KOK, "python")
    return os.path.join(kok, "models", ad)


def activation_path() -> str:
    """Lisans aktivasyon kaydı (G3'te `lisans_durum.py` yazar/okur).

    TOHUMLANMAZ ve pakete GİRMEZ: bu makineye HMAC ile bağlıdır. Kopyalanması
    "başka bilgisayar" hatası üretir; kurucuya girerse dağıtılan her kopya
    lisans kapısını bypass eder.
    """
    return os.path.join(data_root(), "aktivasyon.dat")


def web_root() -> str:
    """Statik oyun dosyalarının kökü (G4'te web.pak bunun yerini alır)."""
    return os.path.join(resource_root(), "web")


def ensure_seeded() -> str:
    """İlk çalıştırma: veri kökünü kur ve `config.json` yoksa şablondan tohumla.

    EXE'de kurulum adımı yok, bu yüzden uygulamanın kendisi yapmak zorunda.
    Best-effort: kopyalama başarısız olsa bile dedektör açılmaya devam etmeli,
    o yüzden asla raise etmez.

    `calib.json` ve `aktivasyon.dat` BİLEREK tohumlanmaz (yukarıdaki gerekçeler).
    """
    try:
        os.makedirs(data_root(), exist_ok=True)
    except Exception as exc:
        print(f"[paths] veri koku olusturulamadi ({exc!r}); varsayilanlarla devam.")
        return ""

    hedef = config_path()
    if os.path.isfile(hedef):
        return hedef

    ornek = ornek_config_path()
    if ornek == hedef or not os.path.isfile(ornek):
        print(f"[paths] tohumlanacak config bulunamadi ('{ornek}').")
        return ""
    try:
        shutil.copy2(ornek, hedef)
        print(f"[paths] '{hedef}' tohumlandi.")
        return hedef
    except Exception as exc:
        print(f"[paths] config tohumlanamadi ({exc!r}); varsayilanlarla devam.")
        return ""
