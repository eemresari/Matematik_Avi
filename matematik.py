"""Matematik Avı — tek giriş noktası.

`start-kiosk.ps1`'in Python karşılığı. Üç ayrı süreç (statik sunucu, dedektör,
tarayıcı) yerine tek bir program; EXE'nin de giriş noktası budur.

Akış:

    paths.ensure_seeded()  ->  statik sunucu  ->  boş WS portu seç
      ->  Chrome --app --start-fullscreen  ->  dedektör (ANA thread)

Lisans kapısı G6'da `_main()`'in en başına girecek — kameradan, porttan ve
sunucudan önce.

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


def _statik_sunucu(port: int) -> threading.Thread:
    """`web/` ağacını servis eden arka plan sunucusu.

    G4 bunu şifreli `web.pak`'i BELLEKTEN servis eden `tools/serve.py` ile
    değiştirecek; o zamana kadar diskten.
    """
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    kok = paths.web_root()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=kok, **kw)

        def log_message(self, *a):      # kiosk'ta her istek için satır basma
            pass

    def calis():
        try:
            ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
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


def main(argv=None) -> int:
    try:
        return _main(argv)
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

    # İlk çalıştırma: yazılabilir veri kökünü kur, config.json'ı tohumla.
    paths.ensure_seeded()

    import main as dedektor        # python/main.py

    if args.kalibrasyon:
        return dedektor.main(["--calibrate"])

    port = _bos_port(args.http_port)
    _statik_sunucu(port)

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
