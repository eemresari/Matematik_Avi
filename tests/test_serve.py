"""tools/serve.py — web.pak'i BELLEKTEN servis eden statik sunucu.

Diskten servis ederken SimpleHTTPRequestHandler sorgu dizesini ve MIME'i
kendisi hallediyordu; bellek yolunda ikisi de ELLE yapilmali. Bu testler tam
o iki tuzagi kilitler.
"""

import threading
import urllib.error
import urllib.request

import pytest

from tools import serve


# ---------------- yol_coz: sorgu dizesi tuzagi ----------------

def test_kok_index_htmle_gider():
    assert serve.yol_coz("/") == "index.html"
    assert serve.yol_coz("") == "index.html"


def test_SORGU_DIZESI_atilir():
    """index.html scriptleri `?v=4`/`?v=6` ekiyle cagiriyor
    (web/index.html:147-153). Atilmazsa HICBIR script bulunamaz ve oyun BOS
    EKRAN acar."""
    assert serve.yol_coz("/js/game.js?v=6") == "js/game.js"
    assert serve.yol_coz("/js/questions.js?v=4") == "js/questions.js"


def test_STYLESHEET_sorgu_dizesi_de_atilir():
    """styles.css?v=9 (index.html:10) — plan yalniz js'leri saymisti."""
    assert serve.yol_coz("/styles.css?v=9") == "styles.css"


def test_fragment_atilir():
    assert serve.yol_coz("/index.html#bolum") == "index.html"


def test_yuzde_kodlama_cozulur():
    assert serve.yol_coz("/js/ge%6Dini.js") == "js/gemini.js"


def test_bas_slash_atilir():
    assert serve.yol_coz("/styles.css") == "styles.css"


def test_ic_ice_yol_korunur():
    assert serve.yol_coz("/fonts/baloo-2.woff2") == "fonts/baloo-2.woff2"


# ---------------- yol_coz: guvenlik ----------------

def test_ust_dizin_REDDEDILIR():
    with pytest.raises(KeyError):
        serve.yol_coz("/../paths.py")


def test_ic_ice_ust_dizin_REDDEDILIR():
    with pytest.raises(KeyError):
        serve.yol_coz("/js/../../lisans.py")


def test_KODLANMIS_ust_dizin_de_REDDEDILIR():
    """%2e%2e -> '..' : kod cozme ONCE yapiliyor, kontrol SONRA olmali."""
    with pytest.raises(KeyError):
        serve.yol_coz("/%2e%2e/paths.py")


# ---------------- MIME tablosu ----------------

def test_js_TEXT_PLAIN_DONMEZ():
    """mimetypes Windows kayit defterine bakar ve bazi makinelerde .js'i
    text/plain doner; tarayici script'i calistirmaz, kiosk bos ekran acar."""
    assert serve.icerik_turu("js/game.js").startswith("text/javascript")


def test_woff2_font_mime():
    """Offline fontlar woff2; yanlis MIME'de tarayici fontu reddeder."""
    assert serve.icerik_turu("fonts/baloo-2.woff2") == "font/woff2"


def test_css_ve_html_mime():
    assert serve.icerik_turu("styles.css").startswith("text/css")
    assert serve.icerik_turu("index.html").startswith("text/html")


def test_bilinmeyen_uzanti_octet_stream():
    assert serve.icerik_turu("a.qqq") == "application/octet-stream"


# ---------------- bellekten servis (uctan uca) ----------------

PAKET = {
    "index.html": b"<h1>Matematik Avi</h1>",
    "js/game.js": b"console.log('oyun');",
    "styles.css": b"body{}",
    "fonts/baloo-2.woff2": b"\x00wOF2",
}


@pytest.fixture
def sunucu():
    import matematik
    port = matematik._bos_port(0)
    t = threading.Thread(target=serve.main, args=([str(port), "."],),
                         kwargs={"paket": PAKET}, daemon=True)
    t.start()
    assert matematik._portu_bekle(port, zaman_asimi=5.0), "sunucu acilmadi"
    return port


def _al(port, yol):
    return urllib.request.urlopen(f"http://127.0.0.1:{port}{yol}", timeout=5)


def test_bellekten_index_servis_edilir(sunucu):
    assert _al(sunucu, "/").read() == b"<h1>Matematik Avi</h1>"


def test_bellekten_SORGU_DIZILI_script(sunucu):
    cevap = _al(sunucu, "/js/game.js?v=6")
    assert cevap.read() == b"console.log('oyun');"
    assert cevap.headers["Content-Type"].startswith("text/javascript")


def test_bellekte_olmayan_dosya_404(sunucu):
    with pytest.raises(urllib.error.HTTPError) as e:
        _al(sunucu, "/yok.js")
    assert e.value.code == 404


def test_ust_dizin_istegi_404(sunucu):
    with pytest.raises(urllib.error.HTTPError) as e:
        _al(sunucu, "/../paths.py")
    assert e.value.code == 404


def test_onbellek_kapali(sunucu):
    """Kiosk her acilista guncel dosyayi yuklemeli."""
    assert "no-store" in _al(sunucu, "/").headers["Cache-Control"]


def test_DISKTEN_servis_te_calisir(tmp_path):
    """paket=None -> diskten servis (kaynaktan calistirma yolu)."""
    import matematik
    (tmp_path / "index.html").write_text("diskten", encoding="utf-8")
    port = matematik._bos_port(0)
    threading.Thread(target=serve.main, args=([str(port), str(tmp_path)],),
                     daemon=True).start()
    assert matematik._portu_bekle(port, zaman_asimi=5.0)
    assert _al(port, "/index.html").read() == b"diskten"
