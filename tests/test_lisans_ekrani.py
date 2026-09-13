"""Lisans kapisinin KARAR YORDAMI (pencere acmadan).

Her hata durumu KENDI mesajini uretmeli: "gecersiz anahtar" deyip suresi
dolmus bir musteriyi destege yollamak kabul edilemez.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

import lisans
import lisans_bicim
import lisans_ekrani
import web_paket

IZ = {"anakart": "a" * 16, "disk": "b" * 16, "mac": "c" * 16}


@pytest.fixture
def imzali(monkeypatch):
    ozel = ed25519.Ed25519PrivateKey.generate()
    pem = ozel.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption())
    acik = ozel.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw).hex()
    monkeypatch.setattr(lisans, "ACIK_ANAHTAR_HEX", acik)

    def uret(**ezme):
        yuk = dict(surum=1, urun=lisans.URUN, tip="demo", kurum="X",
                   anahtar_no=1, paket_no=lisans.PAKET_NO, gecerlilik_gun=7,
                   son_kullanim_ts=int(time.time()) + 86400 * 180,
                   icerik_anahtari=base64.b64encode(b"k" * 32).decode())
        yuk.update(ezme)
        return lisans_bicim.uret(yuk, pem)
    return uret


def _kayit(metin, ilk, en_buyuk=None):
    return {"lisans": metin, "parmak_izi": IZ, "ilk_aktivasyon_ts": ilk,
            "en_buyuk_gorulen_ts": en_buyuk if en_buyuk else ilk}


def test_aktivasyon_yoksa_YOK(imzali):
    durum, yuk = lisans_ekrani.durumu_belirle(None, IZ, time.time())
    assert durum == "yok" and yuk is None


def test_gecerli_aktivasyon(imzali):
    simdi = time.time()
    durum, yuk = lisans_ekrani.durumu_belirle(
        _kayit(imzali(), simdi - 86400), IZ, simdi)
    assert durum == "gecerli"
    assert base64.b64decode(yuk["icerik_anahtari"]) == b"k" * 32


def test_sure_dolunca_DOLDU(imzali):
    simdi = time.time()
    durum, _ = lisans_ekrani.durumu_belirle(
        _kayit(imzali(gecerlilik_gun=1), simdi - 86400 * 3), IZ, simdi)
    assert durum == "doldu"


def test_baska_makinede_BASKA_MAKINE(imzali):
    simdi = time.time()
    baska = {"anakart": "z" * 16, "disk": "y" * 16, "mac": "c" * 16}
    durum, _ = lisans_ekrani.durumu_belirle(
        _kayit(imzali(), simdi - 60), baska, simdi)
    assert durum == "baska_makine"


def test_saat_geri_alinirsa_SAAT(imzali):
    simdi = time.time()
    kayit = _kayit(imzali(), simdi - 86400, en_buyuk=simdi)
    durum, _ = lisans_ekrani.durumu_belirle(kayit, IZ, simdi - 86400 * 5)
    assert durum == "saat"


def test_BASKA_OYUNUN_anahtari_URUN(imzali):
    """KimyaLab anahtari Matematik Avi'ya girilirse net mesaj almali."""
    simdi = time.time()
    durum, _ = lisans_ekrani.durumu_belirle(
        _kayit(imzali(urun="kimyalab"), simdi - 60), IZ, simdi)
    assert durum == "urun"


def test_KALICI_lisans_dolmaz(imzali):
    simdi = time.time()
    metin = imzali(tip="kalici", gecerlilik_gun=None, son_kullanim_ts=None)
    durum, _ = lisans_ekrani.durumu_belirle(
        _kayit(metin, simdi - 86400 * 3650), IZ, simdi)
    assert durum == "gecerli"


def test_makine_bagi_SUREDEN_ONCE_bakilir(imzali):
    """Kopyalanmis bir kuruluma 'sureniz doldu' demek yanlis yonlendirir."""
    simdi = time.time()
    baska = {"anakart": "z" * 16, "disk": "y" * 16, "mac": "x" * 16}
    durum, _ = lisans_ekrani.durumu_belirle(
        _kayit(imzali(gecerlilik_gun=1), simdi - 86400 * 3), baska, simdi)
    assert durum == "baska_makine"


def test_HER_DURUMUN_kendi_mesaji():
    assert set(lisans_ekrani.DURUMLAR) == {
        "yok", "doldu", "baska_makine", "saat", "gecersiz", "surum", "urun"}
    mesajlar = list(lisans_ekrani.DURUMLAR.values())
    assert len(set(mesajlar)) == len(mesajlar), "iki durum ayni mesaji veriyor"
    assert all(m.strip() for m in mesajlar)


def test_sayfa_MESAJ_yer_tutucusu_tasir():
    """ac() mesaji buraya yaziyor; yer tutucu kaybolursa kullanici neden
    lisans istendigini goremez."""
    assert "{{MESAJ}}" in lisans_ekrani._sayfa()


def test_sayfa_ve_mesajlar_MATEMATIK_AVI_diyor():
    """SprayTarih kopyasi; urun adi eksik kalirsa musteri baska oyunun
    penceresini gordugunu sanir.

    Ad GOVDEDE aranir, <title>'da degil: pywebview penceresinin basligini
    create_window belirler, HTML <title>'i gosterilmez."""
    sayfa = lisans_ekrani._sayfa()
    govde = sayfa[sayfa.index("</style>"):]
    assert "MATEMATIK AVI" in govde
    for baskasi in ("KimyaLab", "SprayTarih", "aican"):
        assert baskasi not in sayfa
        assert baskasi not in " ".join(lisans_ekrani.DURUMLAR.values())
    assert "Matematik Avi" in lisans_ekrani.DURUMLAR["urun"]


def test_beklenmeyen_hata_SAHTE_gecersiz_demez(monkeypatch):
    """Dosya yazilamadi gibi bir hata 'anahtar gecerli degil' diye gosterilirse
    kullanici anahtari suclar (yasandi: veri klasoru yokken). Gercek sebep
    mesajda gorunmeli."""
    def patlat(metin):
        raise OSError("disk yazilamadi")
    monkeypatch.setattr(lisans_ekrani, "aktive_et", patlat)
    kopru = lisans_ekrani.Kapi()
    sonuc = kopru.metin_gonder("LDN1.x.y")
    assert sonuc["ok"] is False
    assert "disk yazilamadi" in sonuc["mesaj"]
    assert "gecerli degil" not in sonuc["mesaj"]


KOK = Path(__file__).resolve().parent.parent


def test_LISANS_EKRANI_sifreli_paketin_DISINDA():
    """Kilitli kapinin anahtari kapinin ardinda duramaz.

    web.pak sifreli ve onu cozen anahtar lisansin icinde. Lisans ekrani da
    pakete girseydi, ekrani acabilmek icin once lisans gerekirdi — kimse
    anahtarini giremezdi. Bu yuzden lisans_web/ web/ agacinin DISINDADIR ve
    pakete ham girer.
    """
    sayfa = KOK / "lisans_web" / "index.html"
    assert sayfa.is_file()
    assert (KOK / "web") not in sayfa.parents

    anahtar = b"0" * 32
    dosyalar = web_paket.coz(web_paket.paketle(KOK / "web", anahtar, 1), anahtar)
    assert not [ad for ad in dosyalar if "lisans" in ad.lower()]


def test_HTTP_SUNUCUSU_baslatilmaz():
    """Lisans ekrani webview.create_window(html=...) ile acilir.

    Statik sunucu bu noktada calistirilamaz: servis ettigi sey sifreli paket
    ve icerik anahtari henuz elde yok. Ekran bir HTTP adresinden yuklenmeye
    calisilirsa bos sayfa gelir.
    """
    kaynak = (KOK / "lisans_ekrani.py").read_text(encoding="utf-8")
    for yasak in ("http.server", "tools.serve", "ThreadingHTTPServer",
                  "http://", "127.0.0.1"):
        assert yasak not in kaynak, f"lisans ekrani {yasak} kullaniyor"


def test_KOPRU_HAZIR_DEGILKEN_dugmeler_KALICI_KILITLENMEZ():
    """pywebview js_api'yi pencere cizildikten SONRA enjekte eder.

    O aralikta tiklanirsa `window.pywebview.api...` SENKRON patlar; ham
    `sozVeren().then(...).catch(...)` zincirinde catch hic kurulmadigi icin
    iki dugme de kalici kilitli kalir ve ekranda hicbir aciklama cikmaz —
    musterinin tek caresi programi kapatmaktir. Gercek tarayicida uretildi ve
    dogrulandi; bu test SprayTarih'ten yeniden port edilirse geri gelmesin.
    """
    sayfa = (KOK / "lisans_web" / "index.html").read_text(encoding="utf-8")
    assert "Promise.resolve().then(sozVeren)" in sayfa
    assert "hazir-degil" in sayfa
    # Tiklama yollari kopruye DOGRUDAN degil, api() bekcisi uzerinden gider.
    assert "window.pywebview.api." not in sayfa
    assert "api().dosya_sec()" in sayfa and "api().metin_gonder(" in sayfa
