"""Matematik Avı — tek giriş noktası.

`start-kiosk.ps1`'in Python karşılığı. Üç ayrı süreç (statik sunucu, dedektör,
tarayıcı) yerine tek bir program; EXE'nin de giriş noktası budur.

Akış:

    lisans kapısı (yalnız EXE)  ->  web.pak'i belleğe çöz
      ->  paths.ensure_seeded()  ->  statik sunucu  ->  boş WS portu seç
      ->  Chrome --app --start-fullscreen  ->  dedektör (ANA thread)

Lisans kapısı EN BAŞTA: kamera yoklanmadan, sunucu kalkmadan, port tutulmadan.
Kaynaktan çalıştırmada kapı yoktur (`paths.FROZEN` False) — geliştirme döngüsü
bozulmaz ve `web/` zaten diskte durur.

Tarayıcı dedektörden ÖNCE açılıyor çünkü `web/js/input.js` WebSocket'e üstel
backoff ile yeniden bağlanıyor; dedektör hazır olunca kendiliğinden bağlanır.
Buna karşılık dedektör ANA thread'de kalmalı: cv2'nin önizleme penceresi
(`--calibrate` ve preview modu) ve native kütüphaneler ana thread bekler.
"""

import argparse
import os
import socket
import sys
import threading
import time
import traceback

_KOK = os.path.dirname(os.path.abspath(__file__))
for _yol in (_KOK, os.path.join(_KOK, "python")):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import paths

HTTP_PORT = 8000
WS_PORT = 8765


def _bos_port(tercih: int) -> int:
    """Tercih edilen port meşgulse boş bir port bul.

    Sergide oyunun kazara ikinci kez açılması olağan; ikinci kopyanın sessizce
    çökmesindense farklı bir portta açılması yeğdir.
    """
    for port in (tercih, tercih + 1, tercih + 2, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    return tercih


def _statik_sunucu(port: int, paket=None) -> threading.Thread:
    """Oyunu servis eden arka plan sunucusu.

    `paket`: lisans kapısından geçince bellekte çözülmüş `web.pak` sözlüğü
    (dondurulmuş build). None ise `web/` diskten servis edilir (kaynak).
    """
    from tools import serve

    kok = paths.web_root()

    def calis():
        try:
            serve.main([str(port), kok], paket=paket)
        except Exception as exc:
            print(f"[matematik] statik sunucu durdu: {exc!r}")

    t = threading.Thread(target=calis, name="statik-sunucu", daemon=True)
    t.start()
    return t


def _portu_bekle(port: int, zaman_asimi: float = 8.0) -> bool:
    """Sunucu ayağa kalkana kadar bekle — tarayıcıyı boş sayfaya açmayalım."""
    bitis = time.monotonic() + zaman_asimi
    while time.monotonic() < bitis:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.25)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.15)
    return False


def _tarayici_bul():
    adaylar = []
    for env in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
        kok = os.environ.get(env)
        if kok:
            adaylar.append(os.path.join(kok, "Google", "Chrome",
                                        "Application", "chrome.exe"))
    for env in ("ProgramFiles", "ProgramFiles(x86)"):
        kok = os.environ.get(env)
        if kok:
            adaylar.append(os.path.join(kok, "Microsoft", "Edge",
                                        "Application", "msedge.exe"))
    for yol in adaylar:
        if os.path.isfile(yol):
            return yol
    return None


def _url(port: int, ws_port: int) -> str:
    """Kiosk URL'i. `input=ws` + port tarayıcıya BİLDİRİLMELİ: dedektör ile
    tarayıcı aynı porta bakmazsa oyun sessizce fare moduna düşer."""
    return f"http://127.0.0.1:{port}/?input=ws&host=127.0.0.1&port={ws_port}"


def _tarayici_ac(port: int, ws_port: int, tam_ekran: bool = True) -> None:
    url = _url(port, ws_port)
    exe = _tarayici_bul()
    if exe is None:
        print("[matematik] Chrome/Edge bulunamadi; varsayilan tarayici aciliyor. "
              "Tam ekran icin F11.")
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as exc:
            print(f"[matematik] tarayici acilamadi ({exc!r}); elle acin: {url}")
        return

    # --app + tam ekran: bu modda sayfadaki window.close() (ESC) pencereyi
    # gercekten kapatir ve fazladan karsilama sekmesi acilmaz.
    profil = os.path.join(paths.data_root(), "tarayici-profili")
    args = [exe, f"--app={url}", f"--user-data-dir={profil}",
            "--no-first-run", "--no-default-browser-check",
            "--noerrdialogs", "--disable-infobars",
            "--disable-session-crashed-bubble",
            "--check-for-update-interval=31536000"]
    if tam_ekran:
        args.append("--start-fullscreen")
    try:
        import subprocess
        subprocess.Popen(args, close_fds=True)
    except Exception as exc:
        print(f"[matematik] kiosk penceresi acilamadi ({exc!r}); elle acin: {url}")


def _olumcul(baslik: str, mesaj: str) -> None:
    """Ölümcül hatayı KULLANICIYA göster.

    Dağıtılan EXE konsolsuz derlenir (alıcı çift tıklayınca siyah bir pencere
    değil oyunu görmeli). Bunun bedeli: bir açılış hatası hiçbir yerde
    görünmez — alıcı çift tıklar, hiçbir şey olmaz, elinde tek ipucu yoktur.
    Bu yüzden ölümcül hatalar bir Windows mesaj kutusuyla söylenir.
    """
    print(mesaj)
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, mesaj, baslik, 0x10)  # MB_ICONERROR
    except Exception:
        pass


class LisansReddedildi(SystemExit):
    """Lisans kapısı geçilemedi; uygulama açılmadan durur."""


def filigran_metni(yuk) -> str:
    """Sahnenin köşesinde görünecek metin. Boş dize = filigran gösterilmez.

    KALICI LİSANSTA BOŞ: satılan üründe alıcının adı ekranda durmaz.
    Havuz anahtarında kurum adı yoktur; izlenebilirlik `#anahtar_no` ile
    Lisans Merkezi'ndeki kayıt üzerinden sağlanır.
    """
    import datetime as _dt

    if not yuk or yuk.get("tip") != "demo":
        return ""
    kurum = (yuk.get("kurum") or "").strip() or "Demo"
    parcalar = [kurum]
    son = yuk.get("son_kullanim_ts")
    if son:
        parcalar.append(_dt.datetime.fromtimestamp(son).strftime("%d.%m.%Y"))
    parcalar.append(f"#{yuk.get('anahtar_no', '?')}")
    return " — ".join(parcalar)


def lisans_kapisi(donmus: bool):
    """İçerik anahtarını dön; kaynaktan çalıştırmada None.

    KAMERADAN ÖNCE: dedektör açılışta kamerayı AÇAR; lisansı olmayan birinin
    donanımına dokunmak gereksiz. Statik sunucudan da önce: sunucu yalnız bu
    anahtarla çözülen paketi servis eder.

    `--kalibrasyon` DA KAPIDAN GEÇER: kalibrasyon kamerayı açar ve sonucu veri
    köküne yazar; lisanssız makinede yapılacak işi yoktur. (SprayTarih'te
    `--rapor` muaftı — o hiçbir donanıma dokunmuyor, ziyaretçi sayısı basıyor.)

    Pencere kapatılırsa uygulama DURUR: "anahtar girmedim ama oyun açıldı"
    durumu, korunmak istenen şeyin ta kendisidir.
    """
    import base64

    from tools import serve

    if not donmus:
        return None

    import lisans_durum
    import lisans_ekrani
    import parmak_izi

    try:
        izi = parmak_izi.al()
    except parmak_izi.ParmakIziYok as e:
        raise LisansReddedildi(f"Matematik Avi acilamadi: {e}") from None

    kayit = lisans_durum.oku()
    durum, yuk = lisans_ekrani.durumu_belirle(kayit, izi)

    if durum != "gecerli":
        yuk = lisans_ekrani.ac(lisans_ekrani.DURUMLAR[durum])
        if not yuk:
            raise LisansReddedildi(
                "Matematik Avi acilamadi: gecerli bir lisans yok.")
        kayit = lisans_durum.oku()

    if kayit:
        lisans_durum.saati_ilerlet(kayit)
    serve.FILIGRAN = filigran_metni(yuk)
    return base64.b64decode(yuk["icerik_anahtari"])


def _paketi_yukle(icerik_anahtari):
    """`web.pak`'i BELLEĞE çöz; kaynaktan çalıştırmada ya da anahtarsız None.

    Diske hiçbir şey yazılmaz. None dönerse `tools/serve.py` diskten servis
    eder — bu yalnız kaynaktan çalıştırmada doğru; donmuş build'de `web/`
    ağacı zaten yoktur, yani lisanssız içerik görünmez.
    """
    if not paths.FROZEN or icerik_anahtari is None:
        return None
    import web_paket

    ham_yol = os.path.join(paths.resource_root(), "web.pak")
    try:
        with open(ham_yol, "rb") as f:
            dosyalar = web_paket.coz(f.read(), icerik_anahtari)
    except Exception as exc:      # noqa: BLE001
        raise LisansReddedildi(
            f"Matematik Avi acilamadi: icerik paketi cozulemedi ({exc!r}).\n"
            "Kurulum bozuk olabilir; kurucuyu yeniden calistirin.") from None
    print(f"[matematik] paket bellege alindi: {len(dosyalar)} dosya")
    return dosyalar


def main(argv=None) -> int:
    try:
        return _main(argv)
    except LisansReddedildi as e:
        # SystemExit'ten ONCE yakalanir. Konsolsuz EXE'de `raise SystemExit(mesaj)`
        # metni HICBIR YERE basmaz: parmak izi okunamadiginda ya da paket
        # cozulemediginde alici cift tiklar, hicbir sey olmaz, elinde tek ipucu
        # kalmaz. Kapinin gerekcesi mesaj kutusuyla soylenir.
        _olumcul("Matematik Avi baslatilamadi", str(e))
        return 1
    except SystemExit:
        raise
    except Exception:
        _olumcul("Matematik Avi baslatilamadi",
                 "Matematik Avi acilirken beklenmeyen bir hata olustu.\n\n"
                 + traceback.format_exc(limit=3))
        return 1


def _main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Matematik Avi - kiosk baslatici")
    ap.add_argument("--pencere", action="store_true",
                    help="tam ekran yerine pencere modunda ac")
    ap.add_argument("--tarayicisiz", action="store_true",
                    help="tarayiciyi acma (dedektoru tek basina calistir)")
    ap.add_argument("--onizleme", action="store_true",
                    help="dedektorun OpenCV onizleme penceresini goster")
    ap.add_argument("--kalibrasyon", action="store_true",
                    help="4 kose projeksiyon kalibrasyonunu calistir ve cik")
    ap.add_argument("--http-port", type=int, default=HTTP_PORT)
    args = ap.parse_args(argv)

    # Lisans kapısı HER ŞEYDEN ÖNCE: kamera yoklanmadan, sunucu kalkmadan.
    # Kaynaktan çalıştırmada None döner ve akış eskisi gibi devam eder.
    icerik_anahtari = lisans_kapisi(paths.FROZEN)
    paket = _paketi_yukle(icerik_anahtari)

    # İlk çalıştırma: yazılabilir veri kökünü kur, config.json'ı tohumla.
    paths.ensure_seeded()

    import main as dedektor        # python/main.py

    if args.kalibrasyon:
        return dedektor.main(["--calibrate"])

    port = _bos_port(args.http_port)
    _statik_sunucu(port, paket)

    ws_port = _bos_port(WS_PORT)
    if ws_port != WS_PORT:
        print(f"[matematik] {WS_PORT} mesgul; WebSocket {ws_port} portunda.")

    if not args.tarayicisiz:
        if _portu_bekle(port):
            _tarayici_ac(port, ws_port, tam_ekran=not args.pencere)
        else:
            print(f"[matematik] statik sunucu {port} portunda acilmadi; "
                  "tarayici acilmadi.")

    dedektor_argv = ["--ws-port", str(ws_port)]
    if not args.onizleme:
        dedektor_argv.append("--no-preview")
    return dedektor.main(dedektor_argv)


if __name__ == "__main__":
    raise SystemExit(main())
