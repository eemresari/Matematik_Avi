"""matematik.py — tek giris noktasinin donanimsiz dogrulanabilen parcalari.

Kamera, mediapipe ve tarayici HIC calistirilmaz.
"""

import socket
import threading
import urllib.error
import urllib.request

import pytest

import matematik


# ---------------- port secimi ----------------

def test_bos_port_tercihi_dondurur():
    port = matematik._bos_port(0)      # 0 = isletim sistemi bos port versin
    assert isinstance(port, int) and port > 0


def test_bos_port_mesgulse_BASKA_port_secer():
    """Sergide oyun kazara ikinci kez acilir; ikinci kopya sessizce olmemeli."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as mesgul:
        mesgul.bind(("127.0.0.1", 0))
        alinan = mesgul.getsockname()[1]
        mesgul.listen(1)
        secilen = matematik._bos_port(alinan)
        assert secilen != alinan


def test_portu_bekle_kapali_portta_False():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        kapali = s.getsockname()[1]
    assert matematik._portu_bekle(kapali, zaman_asimi=0.5) is False


def test_portu_bekle_acik_portta_True():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    try:
        assert matematik._portu_bekle(srv.getsockname()[1], zaman_asimi=2.0) is True
    finally:
        srv.close()


# ---------------- kiosk URL'i ----------------

def test_url_ws_modunu_ve_portu_tasir():
    """Tarayici WS portunu URL'den ogreniyor; yanlissa oyun sessizce fare
    moduna duser (input.js varsayilani 'mouse')."""
    url = matematik._url(8000, 8770)
    assert "input=ws" in url
    assert "port=8770" in url
    assert url.startswith("http://127.0.0.1:8000/")


# ---------------- statik sunucu ----------------

@pytest.fixture
def sunucu():
    port = matematik._bos_port(0)
    matematik._statik_sunucu(port)
    assert matematik._portu_bekle(port, zaman_asimi=5.0), "statik sunucu acilmadi"
    return port


def _al(port: int, yol: str):
    return urllib.request.urlopen(f"http://127.0.0.1:{port}{yol}", timeout=5)


def test_sunucu_index_servis_eder(sunucu):
    cevap = _al(sunucu, "/")
    assert cevap.status == 200
    assert b"Matematik" in cevap.read()


def test_sunucu_SORGU_DIZILI_scripti_servis_eder(sunucu):
    """index.html scriptleri `?v=6` ekiyle cagiriyor (web/index.html:147-153).

    Sorgu dizisi atilmazsa 404 doner ve oyun BOS EKRAN acar. G4'te web.pak'i
    bellekten servis eden yol_coz() ayni tuzagi tasiyacak; davranis burada
    kilitleniyor."""
    assert _al(sunucu, "/js/game.js?v=6").status == 200


def test_sunucu_sorgu_dizili_STYLESHEET_servis_eder(sunucu):
    """styles.css?v=9 — plan yalniz js'leri sayiyordu, css'te de var."""
    assert _al(sunucu, "/styles.css?v=9").status == 200


def test_sunucu_olmayan_yolda_404(sunucu):
    with pytest.raises(urllib.error.HTTPError) as e:
        _al(sunucu, "/yok-boyle-bir-dosya.js")
    assert e.value.code == 404
