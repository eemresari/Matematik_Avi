"""Matematik Avi'nin lisans kapisi: urune ozel sabitler + dogrulama.

TASIYICI DIREK: EXE'de yalniz ACIK anahtar durur. Ozel anahtar Lisans
Merkezi'nde (~/.luden-lisans/urunler/matematik/ozel.key), bu depoda DEGIL.
Imza uretmek icin ozel anahtari calmak gerekir; tersine muhendisligi yoktur.

HICBIR TEST GERCEK OZEL ANAHTARA BAGIMLI DEGILDIR: testler kendi gecici
ciftini uretir ve ACIK_ANAHTAR_HEX'i ezer.

Icerik anahtari yukun icinde acik durur ve bu bir kayip DEGILDIR: lisansa
sahip kisi zaten oyunu calistirabiliyor. Korunan sey, lisansi OLMAYAN kisinin
web.pak'i cozememesidir.
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

KOK = Path(__file__).resolve().parent.parent


@pytest.fixture
def cift(monkeypatch):
    ozel = ed25519.Ed25519PrivateKey.generate()
    pem = ozel.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption())
    acik = ozel.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw).hex()
    monkeypatch.setattr(lisans, "ACIK_ANAHTAR_HEX", acik)
    return pem


def _yuk(**ezme):
    temel = dict(surum=1, urun=lisans.URUN, tip="demo",
                 kurum="Konya Bilim Merkezi", anahtar_no=42,
                 paket_no=lisans.PAKET_NO, gecerlilik_gun=7,
                 son_kullanim_ts=int(time.time()) + 86400 * 180,
                 icerik_anahtari=base64.b64encode(b"k" * 32).decode())
    temel.update(ezme)
    return temel


def test_ACIK_ANAHTAR_gercek_deger():
    """Yer tutucu ('00'*32) kalirsa hicbir gercek anahtar dogrulanamaz."""
    assert lisans.ACIK_ANAHTAR_HEX != "00" * 32
    assert len(lisans.ACIK_ANAHTAR_HEX) == 64
    bytes.fromhex(lisans.ACIK_ANAHTAR_HEX)      # gecerli hex mi


def test_urun_kodu_matematik():
    assert lisans.URUN == "matematik"


def test_uret_dogrula_turu(cift):
    metin = lisans_bicim.uret(_yuk(), cift)
    cozulen = lisans.dogrula(metin)
    assert cozulen["kurum"] == "Konya Bilim Merkezi"
    assert cozulen["anahtar_no"] == 42


def test_BASKA_OYUNUN_anahtari_reddedilir(cift):
    """KimyaLab anahtari Matematik Avi'yi acmamali; urun kodu imzanin icinde."""
    metin = lisans_bicim.uret(_yuk(urun="kimyalab"), cift)
    with pytest.raises(lisans.UrunHatasi):
        lisans.dogrula(metin)


def test_kurcalanmis_yuk_reddedilir(cift):
    import json
    metin = lisans_bicim.uret(_yuk(gecerlilik_gun=7), cift)
    _, govde, imza = metin.split(".")
    yuk = json.loads(base64.urlsafe_b64decode(govde + "=="))
    yuk["gecerlilik_gun"] = 9999
    yeni = base64.urlsafe_b64encode(
        json.dumps(yuk, separators=(",", ":"),
                   ensure_ascii=False).encode()).decode().rstrip("=")
    with pytest.raises(lisans.ImzaHatasi):
        lisans.dogrula(f"LDN1.{yeni}.{imza}")


def test_yanlis_paket_no(cift):
    metin = lisans_bicim.uret(_yuk(paket_no=99), cift)
    with pytest.raises(lisans.SurumHatasi):
        lisans.dogrula(metin)


def test_gecmis_son_kullanim(cift):
    metin = lisans_bicim.uret(_yuk(son_kullanim_ts=int(time.time()) - 10), cift)
    with pytest.raises(lisans.SuresiGecmis):
        lisans.dogrula(metin)


def test_dosya_ve_metin_AYNI_sonuc(cift, tmp_path):
    """Iki teslim yolu tek dogrulama yoluna inmeli."""
    metin = lisans_bicim.uret(_yuk(), cift)
    dosya = tmp_path / "lisans.dat"
    dosya.write_text(metin, encoding="utf-8")
    assert lisans.dogrula(dosya.read_text(encoding="utf-8")) == \
        lisans.dogrula(metin)


def test_bosluk_ve_satir_sonu_temizlenir(cift):
    """E-postadan yapistirilan blok satir sonu ve bosluk tasir."""
    metin = lisans_bicim.uret(_yuk(), cift)
    kirli = "  " + metin[:20] + "\n" + metin[20:] + "\r\n  "
    assert lisans.dogrula(kirli)["anahtar_no"] == 42


def test_baslik_yanlissa_anlamli_hata(cift):
    with pytest.raises(lisans.LisansHatasi, match="anahtar"):
        lisans.dogrula("bu bir lisans degil")


# --- sizinti kilitleri: uretim yetenegi bu depoda OLMAMALI ---

def test_URETIM_MODULLERI_bu_depoda_YOK():
    """imza_deposu.py ve lisans_uret.py Lisans Merkezi'ne tasindi. Buraya
    geri sizarlarsa ozel anahtar da pesinden gelir."""
    for ad in ("imza_deposu.py", "lisans_uret.py"):
        assert not (KOK / ad).exists(), f"{ad} bu depoda olmamali"


def test_OZEL_ANAHTAR_dosyasi_depoda_YOK():
    """Ozel anahtar sizarsa herkes key uretebilir — her sey biter."""
    sizanlar = [p.name for p in KOK.rglob("*.key")
                if ".venv" not in p.parts and "dist" not in p.parts
                and "build" not in p.parts and "node_modules" not in p.parts]
    assert not sizanlar, f"depoda anahtar dosyasi var: {sizanlar}"


def test_ACIK_ANAHTAR_merkezdeki_ciftle_AYNI():
    """Gomulu acik anahtar, Lisans Merkezi'ndeki cifte ait olmali.

    Elle kopyalanan 64 haneli bir dizgede tek hane hatasi derlemeyi de,
    yukaridaki testleri de gecer (hepsi kendi gecici ciftini uretir) ve ancak
    MUSTERI anahtarini girdiginde "gecerli degil" diye patlar. Burada gercek
    kaynakla karsilastiriliyor.

    Merkez'in kurulu olmadigi makinede atlanir: acik.key depo disindadir
    (~/.luden-lisans/), CI'da ve baska bir gelistirici makinesinde yoktur.
    """
    kaynak = (Path.home() / ".luden-lisans" / "urunler" / lisans.URUN /
              "acik.key")
    if not kaynak.exists():
        pytest.skip("Lisans Merkezi bu makinede kurulu degil")
    assert lisans.ACIK_ANAHTAR_HEX == kaynak.read_text(encoding="utf-8").strip()
