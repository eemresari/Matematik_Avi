"""web_paket.py — sifreli icerik paketi.

Oyun mantigi JS'te (questions.js soru havuzu, tokens.js, game.js). Nuitka
Python'i makine koduna cevirir ama web/ ham konursa EXE'nin yaninda okunabilir
kaynak olarak durur. Bu testler paketin GERCEKTEN sifreli oldugunu kilitler.
"""

import os

import pytest

import web_paket

ANAHTAR = b"0" * 32
BASKA_ANAHTAR = b"1" * 32


@pytest.fixture
def agac(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Matematik Avi</h1>", encoding="utf-8")
    (tmp_path / "js").mkdir()
    (tmp_path / "js" / "questions.js").write_text(
        "const SORULAR = ['7 x 8 = 56'];", encoding="utf-8")
    (tmp_path / "fonts").mkdir()
    (tmp_path / "fonts" / "baloo.woff2").write_bytes(b"\x00wOF2 sahte")
    return tmp_path


def test_paketle_coz_gidis_donus(agac):
    paket = web_paket.paketle(agac, ANAHTAR, 1)
    dosyalar = web_paket.coz(paket, ANAHTAR)
    assert dosyalar["index.html"] == b"<h1>Matematik Avi</h1>"
    assert dosyalar["js/questions.js"] == b"const SORULAR = ['7 x 8 = 56'];"
    assert dosyalar["fonts/baloo.woff2"] == b"\x00wOF2 sahte"


def test_yollar_POSIX_ayraciyla(agac):
    """Tarayici '/' ister; Windows'ta paketlenip '\\' yazilirsa 404 doner."""
    dosyalar = web_paket.coz(web_paket.paketle(agac, ANAHTAR, 1), ANAHTAR)
    assert "js/questions.js" in dosyalar
    assert not any("\\" in ad for ad in dosyalar)


def test_paket_no_ANAHTARSIZ_okunur(agac):
    """EXE 'bu anahtar bu surum icin mi' diyebilmeli; yoksa surum
    uyusmazliginda kullaniciya 'gecersiz anahtar' gibi YANLIS mesaj gider."""
    paket = web_paket.paketle(agac, ANAHTAR, 7)
    assert web_paket.paket_no_oku(paket) == 7


def test_YANLIS_anahtar_cozemez(agac):
    paket = web_paket.paketle(agac, ANAHTAR, 1)
    with pytest.raises(Exception):
        web_paket.coz(paket, BASKA_ANAHTAR)


def test_yabanci_baslik_reddedilir():
    with pytest.raises(ValueError):
        web_paket.paket_no_oku(b"STPAK1\n" + b"\x00" * 32)


def test_bozuk_govde_reddedilir(agac):
    """AES-GCM butunluk saglar: tek bayt degisse cozulme BASARISIZ olmali."""
    paket = bytearray(web_paket.paketle(agac, ANAHTAR, 1))
    paket[-1] ^= 0xFF
    with pytest.raises(Exception):
        web_paket.coz(bytes(paket), ANAHTAR)


def test_SORU_METINLERI_pakette_DUZ_GECMEZ(agac):
    """G4'un asil amaci. Dogrulama tablosu #5 bunu ariyor."""
    paket = web_paket.paketle(agac, ANAHTAR, 1)
    assert b"7 x 8 = 56" not in paket
    assert b"SORULAR" not in paket


def test_DOSYA_ADLARI_da_pakette_gecmez(agac):
    """Sifreleme zip'in USTUNDE: ad da icerik de gorunmemeli."""
    paket = web_paket.paketle(agac, ANAHTAR, 1)
    assert b"questions.js" not in paket
    assert b"index.html" not in paket


def test_bos_agac_paketlenebilir(tmp_path):
    assert web_paket.coz(web_paket.paketle(tmp_path, ANAHTAR, 1), ANAHTAR) == {}


def test_GERCEK_web_agaci_paketlenir():
    """Depodaki gercek web/ agaci — sentetik degil."""
    import paths
    kok = paths.web_root()
    if not os.path.isdir(kok):
        pytest.skip("web/ yok")
    dosyalar = web_paket.coz(web_paket.paketle(kok, ANAHTAR, 1), ANAHTAR)
    assert "index.html" in dosyalar
    assert "js/game.js" in dosyalar
