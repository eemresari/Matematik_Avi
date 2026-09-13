#!/usr/bin/env python3
"""Matematik Avı kiosk statik sunucusu — tarayıcı önbelleği KAPALI.

İki iş yapar:

1. **Şifreli `web.pak`'i BELLEKTEN servis eder.** Dondurulmuş build'de `web/`
   ağacı diskte yoktur; lisans kapısından geçince paket bellekte çözülür ve
   buraya verilir. Diske hiçbir şey yazılmaz.
2. **`Cache-Control: no-store`.** Stok `python -m http.server` tarayıcının
   script'leri önbelleğe almasına izin veriyor; sergi güncellendikten sonra
   kiosk eski sürümü göstermeye devam edebiliyordu.

Kullanım:
    python tools/serve.py [PORT] [DIZIN]
"""

import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# Elle MIME tablosu: `mimetypes` Windows kayıt defterine bakar ve bazı
# makinelerde `.js`'i `text/plain` döner — tarayıcı script'i çalıştırmaz, kiosk
# boş ekran açar. Diskten servis ederken SimpleHTTPRequestHandler kendi
# tablosunu kullanıyordu; bellek yolunda aynı tuzağa düşmemek için liste sabit.
MIME = {
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    # Çevrimdışı fontlar woff2; yanlış MIME'de tarayıcı fontu reddeder ve
    # sergide tofu kutuları çıkar.
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
}


def yol_coz(istek: str) -> str:
    """HTTP yolunu paket sözlüğü anahtarına çevir.

    SORGU DİZESİ ATILIR: `index.html` script'leri sürüm eki taşıyor
    (`js/game.js?v=6`, `styles.css?v=9`). Atılmazsa bellek sözlüğünde hiçbiri
    bulunamaz ve oyun BOŞ EKRAN açar. Diskten servis ederken
    SimpleHTTPRequestHandler bunu zaten yapıyordu; bellek yolunda elle.
    """
    from urllib.parse import unquote

    # Kod çözme ÖNCE, güvenlik kontrolü SONRA: `%2e%2e` de `..` demektir.
    yol = unquote(istek.split("?", 1)[0].split("#", 1)[0]).lstrip("/")
    if not yol:
        return "index.html"
    parcalar = yol.replace("\\", "/").split("/")
    if any(p in ("..", ".") or not p for p in parcalar):
        raise KeyError(f"guvenli olmayan yol: {istek}")
    return "/".join(parcalar)


def icerik_turu(ad: str) -> str:
    _, uzanti = os.path.splitext(ad)
    return MIME.get(uzanti.lower(), "application/octet-stream")


class OnbelleksizHandler(SimpleHTTPRequestHandler):
    """Dosyaları servis et ama tarayıcıya asla önbelleğe alma de."""

    protocol_version = "HTTP/1.1"

    # Çözülmüş web.pak: {"js/game.js": b"...", ...}. None ise diskten servis.
    # main(paket=...) bunu bir ALT SINIFA bağlar; temel sınıf hep None kalır.
    bellek = None

    def _gonder(self, kod: int, tur: str, govde: bytes) -> None:
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(govde)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if self.bellek is None:
            super().do_GET()
            return
        try:
            ad = yol_coz(self.path)
        except KeyError:
            self.send_error(404, "Not Found")
            return
        govde = self.bellek.get(ad)
        if govde is None:
            self.send_error(404, "Not Found")
            return
        self._gonder(200, icerik_turu(ad), govde)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):      # kiosk'ta her istek için satır basma
        pass


def main(argv=None, paket=None) -> int:
    # argv PARAMETRE (sadece sys.argv değil): matematik.py bu sunucuyu tek EXE
    # içinde bir THREAD'de çalıştırıyor, orada sys.argv oyuna ait.
    argv = list(sys.argv[1:] if argv is None else argv)
    port = int(argv[0]) if len(argv) > 0 else 8000
    dizin = argv[1] if len(argv) > 1 else "."
    sinif = OnbelleksizHandler
    if paket is not None:
        sinif = type("BellekHandler", (OnbelleksizHandler,), {"bellek": paket})
    handler = partial(sinif, directory=dizin)
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        kaynak = f"bellek, {len(paket)} dosya" if paket is not None else dizin
        print(f"[serve] http://127.0.0.1:{port}/  ({kaynak})")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[serve] durdu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
