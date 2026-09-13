"""Acilis kapisi: lisans; KAMERADAN, SUNUCUDAN ve PORTTAN once.

Dedektor acilista kamerayi ACAR ve statik sunucu web/'i servis eder; ikisi de
lisans dogrulanmadan olmamali. Sira burada kilitlenir — bir gun "once sunucu
kalksin, sonra bakariz" diye yer degistirirse lisanssiz oyun acilir.

Kaynaktan calistirmada (paths.FROZEN False) kapi YOKTUR: gelistirme dongusu
bozulmamali; web/ zaten diskten okunuyor.
"""

from __future__ import annotations

import base64
import inspect
import json
import re
import threading
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

import lisans_durum
import lisans_ekrani
import matematik
import parmak_izi
import paths
import web_paket
from tools import serve

IZ = {"anakart": "a" * 16, "disk": "b" * 16, "mac": "c" * 16}


@pytest.fixture(autouse=True)
def filigrani_temizle(monkeypatch):
    """serve.FILIGRAN modul duzeyinde; bir test digerini kirletmesin."""
    monkeypatch.setattr(serve, "FILIGRAN", "")


# --------------------------------------------------------------------------- #
# Sira kilidi
# --------------------------------------------------------------------------- #

def test_kapi_SUNUCUDAN_ve_DEDEKTORDEN_once():
    kaynak = inspect.getsource(matematik._main)
    kapi = kaynak.index("lisans_kapisi(")
    assert kapi < kaynak.index("ensure_seeded(")
    assert kapi < kaynak.index("import main as dedektor")
    assert kapi < kaynak.index("_bos_port(")
    assert kapi < kaynak.index("_statik_sunucu(")


def test_KALIBRASYON_da_kapidan_gecer():
    """Kalibrasyon kamerayi acar ve veri kokune yazar; lisanssiz makinede
    yapilacak isi yoktur. (SprayTarih'te `--rapor` muafti — o hicbir donanima
    dokunmuyor, yalnizca ziyaretci sayisi basiyor.)"""
    kaynak = inspect.getsource(matematik._main)
    assert kaynak.index("lisans_kapisi(") < kaynak.index("args.kalibrasyon")


def test_COZULEN_PAKET_sunucuya_verilir():
    """Kapidan cikan anahtarla cozulen paket servis edilmezse donmus EXE bos
    ekran acar: web/ agaci diskte yoktur."""
    kaynak = inspect.getsource(matematik._main)
    assert "_paketi_yukle(icerik_anahtari)" in kaynak
    assert "_statik_sunucu(port, paket)" in kaynak


# --------------------------------------------------------------------------- #
# lisans_kapisi
# --------------------------------------------------------------------------- #

def test_kaynaktan_calistirmada_kapi_YOK(monkeypatch):
    monkeypatch.setattr(parmak_izi, "al",
                        lambda: pytest.fail("kaynaktan calisirken parmak izi okunmamali"))
    assert matematik.lisans_kapisi(False) is None
    assert serve.FILIGRAN == ""


def test_gecerli_aktivasyon_ANAHTARI_doner(monkeypatch):
    anahtar = b"k" * 32
    yuk = {"tip": "kalici", "icerik_anahtari": base64.b64encode(anahtar).decode()}
    monkeypatch.setattr(parmak_izi, "al", lambda: IZ)
    monkeypatch.setattr(lisans_durum, "oku", lambda: {"lisans": "x", "parmak_izi": IZ})
    monkeypatch.setattr(lisans_durum, "saati_ilerlet", lambda k: None)
    monkeypatch.setattr(lisans_ekrani, "durumu_belirle", lambda k, i: ("gecerli", yuk))
    monkeypatch.setattr(lisans_ekrani, "ac",
                        lambda m: pytest.fail("gecerli lisansta pencere acilmamali"))
    assert matematik.lisans_kapisi(True) == anahtar
    assert serve.FILIGRAN == ""       # kalici lisansta filigran yok


def test_pencere_kapatilirsa_UYGULAMA_DURUR(monkeypatch):
    """'anahtar girmedim ama oyun acildi' korunmak istenen seyin ta kendisi."""
    monkeypatch.setattr(parmak_izi, "al", lambda: IZ)
    monkeypatch.setattr(lisans_durum, "oku", lambda: None)
    monkeypatch.setattr(lisans_ekrani, "durumu_belirle", lambda k, i: ("yok", None))
    monkeypatch.setattr(lisans_ekrani, "ac", lambda m: None)
    with pytest.raises(matematik.LisansReddedildi):
        matematik.lisans_kapisi(True)


def test_pencereden_gecince_anahtar_ve_filigran(monkeypatch):
    anahtar = b"z" * 32
    yuk = {"tip": "demo", "kurum": "Konya Bilim Merkezi", "anahtar_no": 7,
           "son_kullanim_ts": 1_800_000_000,
           "icerik_anahtari": base64.b64encode(anahtar).decode()}
    acilan = []
    monkeypatch.setattr(parmak_izi, "al", lambda: IZ)
    monkeypatch.setattr(lisans_durum, "oku", lambda: None)
    monkeypatch.setattr(lisans_durum, "saati_ilerlet", lambda k: None)
    monkeypatch.setattr(lisans_ekrani, "durumu_belirle", lambda k, i: ("yok", None))
    monkeypatch.setattr(lisans_ekrani, "ac", lambda m: acilan.append(m) or yuk)
    assert matematik.lisans_kapisi(True) == anahtar
    assert acilan == [lisans_ekrani.DURUMLAR["yok"]]
    assert "Konya Bilim Merkezi" in serve.FILIGRAN
    assert "#7" in serve.FILIGRAN


def test_parmak_izi_okunamazsa_anlamli_hata(monkeypatch):
    def patlat():
        raise parmak_izi.ParmakIziYok("kimlik okunamadi")
    monkeypatch.setattr(parmak_izi, "al", patlat)
    with pytest.raises(matematik.LisansReddedildi, match="kimlik"):
        matematik.lisans_kapisi(True)


def test_LisansReddedildi_SystemExit_turevi():
    assert issubclass(matematik.LisansReddedildi, SystemExit)


def test_RED_GEREKCESI_mesaj_kutusuyla_gosterilir(monkeypatch):
    """Konsolsuz EXE'de `raise SystemExit(mesaj)` metni HICBIR YERE basmaz;
    alici cift tiklar, hicbir sey olmaz. main() bu yuzden LisansReddedildi'yi
    SystemExit'ten ONCE yakalar. (SprayTarih'te bu yok — orada parmak izi
    okunamadiginda uygulama tamamen sessizce oluyor.)"""
    gosterilen = []

    def patlat(argv):
        raise matematik.LisansReddedildi(
            "Matematik Avi acilamadi: kimlik okunamadi")

    monkeypatch.setattr(matematik, "_olumcul",
                        lambda b, m: gosterilen.append((b, m)))
    monkeypatch.setattr(matematik, "_main", patlat)
    assert matematik.main([]) == 1
    assert len(gosterilen) == 1
    assert "kimlik okunamadi" in gosterilen[0][1]


# --------------------------------------------------------------------------- #
# _paketi_yukle
# --------------------------------------------------------------------------- #

def test_paket_kaynaktan_calistirmada_None(monkeypatch):
    monkeypatch.setattr(paths, "FROZEN", False)
    assert matematik._paketi_yukle(b"k" * 32) is None


def test_paket_anahtarsiz_None(monkeypatch):
    monkeypatch.setattr(paths, "FROZEN", True)
    assert matematik._paketi_yukle(None) is None


def test_paket_BELLEGE_cozulur(monkeypatch, tmp_path):
    anahtar = b"q" * 32
    kaynak = tmp_path / "web"
    (kaynak / "js").mkdir(parents=True)
    (kaynak / "index.html").write_text("<h1>x</h1>", encoding="utf-8")
    (kaynak / "js" / "game.js").write_text("// oyun", encoding="utf-8")
    yan = tmp_path / "yan"
    yan.mkdir()
    (yan / "web.pak").write_bytes(web_paket.paketle(kaynak, anahtar, 1))
    monkeypatch.setattr(paths, "FROZEN", True)
    monkeypatch.setattr(paths, "resource_root", lambda: str(yan))
    dosyalar = matematik._paketi_yukle(anahtar)
    assert dosyalar["js/game.js"] == b"// oyun"
    assert not (yan / "web").exists()      # diske hicbir sey yazilmaz


def test_paket_cozulemezse_ANLAMLI_hata(monkeypatch, tmp_path):
    """Bozuk kurulumda 'gecersiz anahtar' demek musteriyi yanlis yere yollar."""
    monkeypatch.setattr(paths, "FROZEN", True)
    monkeypatch.setattr(paths, "resource_root", lambda: str(tmp_path))
    (tmp_path / "web.pak").write_bytes(b"bozuk")
    with pytest.raises(matematik.LisansReddedildi, match="paketi cozulemedi"):
        matematik._paketi_yukle(b"k" * 32)


# --------------------------------------------------------------------------- #
# Filigran metni
# --------------------------------------------------------------------------- #

def test_filigran_kalici_lisansta_BOS():
    assert matematik.filigran_metni({"tip": "kalici", "kurum": "X",
                                     "anahtar_no": 1}) == ""
    assert matematik.filigran_metni(None) == ""


def test_filigran_demoda_kurum_tarih_no():
    metin = matematik.filigran_metni({"tip": "demo", "kurum": "Kurum A",
                                      "anahtar_no": 12,
                                      "son_kullanim_ts": 1_800_000_000})
    assert metin.startswith("Kurum A")
    assert re.search(r"\d{2}\.\d{2}\.\d{4}", metin)
    assert metin.endswith("#12")


def test_filigran_kurumsuz_demo():
    assert matematik.filigran_metni({"tip": "demo", "anahtar_no": 3}) == "Demo — #3"


# --------------------------------------------------------------------------- #
# GET /filigran.json
# --------------------------------------------------------------------------- #

def _sunucu_ac(sinif, dizin):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(sinif, directory=dizin))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


@pytest.fixture
def sunucu(tmp_path):
    class H(serve.OnbelleksizHandler):
        def log_message(self, *a):
            pass
    httpd = _sunucu_ac(H, str(tmp_path))
    yield httpd.server_address[1]
    httpd.shutdown()


def test_filigran_json(sunucu, monkeypatch):
    monkeypatch.setattr(serve, "FILIGRAN", "Kurum A — 01.01.2027 — #5")
    with urllib.request.urlopen(f"http://127.0.0.1:{sunucu}/filigran.json",
                                timeout=3) as r:
        assert r.status == 200
        assert r.headers["Content-Type"].startswith("application/json")
        assert "no-store" in r.headers["Cache-Control"]
        assert json.loads(r.read()) == {"metin": "Kurum A — 01.01.2027 — #5"}


def test_filigran_json_bos(sunucu):
    with urllib.request.urlopen(f"http://127.0.0.1:{sunucu}/filigran.json",
                                timeout=3) as r:
        assert json.loads(r.read()) == {"metin": ""}


def test_filigran_json_PAKET_servis_edilirken_de_calisir(tmp_path, monkeypatch):
    """Asil calisma sekli bu: donmus EXE'de sunucu BELLEKTEN servis eder ve
    /filigran.json paket sozlugunde YOKTUR. Kontrol `bellek is None` dalindan
    once gelmezse istek 404 doner ve filigran hic cizilmez."""
    monkeypatch.setattr(serve, "FILIGRAN", "Kurum B — #9")

    class H(serve.OnbelleksizHandler):
        bellek = {"index.html": b"<h1>x</h1>"}

        def log_message(self, *a):
            pass

    httpd = _sunucu_ac(H, str(tmp_path))
    try:
        port = httpd.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/filigran.json",
                                    timeout=3) as r:
            assert json.loads(r.read()) == {"metin": "Kurum B — #9"}
    finally:
        httpd.shutdown()


# --------------------------------------------------------------------------- #
# Oyun tarafi — statik kilit
# --------------------------------------------------------------------------- #

def test_oyun_filigrani_okur_ve_cizer():
    kok = Path(matematik.__file__).resolve().parent
    js = (kok / "web" / "js" / "game.js").read_text(encoding="utf-8")
    assert "/filigran.json" in js
    assert 'className = "filigran"' in js
    css = (kok / "web" / "styles.css").read_text(encoding="utf-8")
    assert ".filigran{" in css


def test_filigran_FARE_ROZETIYLE_cakismaz():
    """input.js'in 'FARE MODU' rozeti SOL-altta sabit; filigran sag-altta
    olmazsa ikisi ust uste biner ve ikisi de okunmaz olur."""
    kok = Path(matematik.__file__).resolve().parent
    css = (kok / "web" / "styles.css").read_text(encoding="utf-8")
    kural = css[css.index(".filigran{"):]
    kural = kural[:kural.index("}")]
    assert "right:" in kural and "left:" not in kural
    js = (kok / "web" / "js" / "input.js").read_text(encoding="utf-8")
    assert '"left:14px", "bottom:12px"' in js
