"""paths.py — salt okunur paket icerigi vs yazilabilir kullanici verisi.

Hicbir test donanim/kamera istemez. FROZEN modul global'i monkeypatch ile
cevrilir; gercekten derlemeye gerek yok.
"""

import os

import pytest

import paths


@pytest.fixture
def donmus(monkeypatch, tmp_path):
    """FROZEN=True + EXE'yi tmp bir dizinde gosteren sahte sys.executable."""
    exe_dir = tmp_path / "dist"
    exe_dir.mkdir()
    monkeypatch.setattr(paths, "FROZEN", True)
    monkeypatch.setattr(paths.sys, "executable", str(exe_dir / "matematik.exe"))
    monkeypatch.delenv(paths.VERI_KOKU_ENV, raising=False)
    return exe_dir


@pytest.fixture
def yerel_veri(monkeypatch, tmp_path):
    """Donmus modda %LOCALAPPDATA% tmp'ye yonlendirilir."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    return tmp_path / "AppData"


# ---------------- kaynak (gelistirme) modu ----------------

def test_kaynakta_donmus_degil():
    """Testler kaynaktan kosuyor; FROZEN False olmali."""
    assert paths.FROZEN is False


def test_kaynakta_resource_root_depo_koku():
    assert paths.resource_root() == os.path.dirname(os.path.abspath(paths.__file__))


def test_kaynakta_veri_koku_python_dizini():
    """Kaynakta veri koku python/ — config.json ve calib.json BUGUN orada.

    Plan 'depo koku' diyordu; python/ secildi ki `cd python && python main.py`
    akisi bozulmasin ve ikinci bir divergent config.json dogmasin.
    """
    assert paths.data_root() == os.path.join(paths.resource_root(), "python")


def test_kaynakta_config_gercekten_var():
    """Secilen yol hayali degil: depodaki dosyayi gostermeli."""
    assert os.path.isfile(paths.config_path())


def test_kaynakta_model_gercekten_var():
    assert os.path.isfile(paths.model_path())


# ---------------- donmus (EXE) modu ----------------

def test_donmusta_resource_root_exe_yani(donmus):
    assert paths.resource_root() == str(donmus)


def test_donmusta_veri_koku_localappdata(donmus, yerel_veri):
    assert paths.data_root() == str(yerel_veri / paths.UYGULAMA_ADI)


def test_donmusta_veri_koku_resource_roottan_AYRI(donmus, yerel_veri):
    """Kritik ayrim: Program Files'a kurulu EXE'nin yanina yazilamaz."""
    assert paths.data_root() != paths.resource_root()


def test_donmusta_model_exe_yaninda(donmus):
    assert paths.model_path() == os.path.join(str(donmus), "models",
                                              "hand_landmarker.task")


def test_donmusta_ornek_config_ADI_config_json_DEGIL(donmus):
    """Sablon 'config.json' adiyla girerse G9'un dist taramasi onu da
    yasakli sayar (VERI_DOSYALARI 'config.json'u kapsiyor)."""
    assert os.path.basename(paths.ornek_config_path()) != "config.json"
    assert paths.ornek_config_path() == os.path.join(str(donmus), "config.ornek.json")


# ---------------- ortam degiskeni ezmesi ----------------

def test_env_veri_kokunu_ezer(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.VERI_KOKU_ENV, str(tmp_path / "tasinabilir"))
    assert paths.data_root() == str(tmp_path / "tasinabilir")


def test_env_donmusta_da_ezer(donmus, yerel_veri, monkeypatch, tmp_path):
    monkeypatch.setenv(paths.VERI_KOKU_ENV, str(tmp_path / "tasinabilir"))
    assert paths.data_root() == str(tmp_path / "tasinabilir")


# ---------------- turetilmis yollar ----------------

def test_yollar_veri_kokunun_altinda(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.VERI_KOKU_ENV, str(tmp_path))
    for yol in (paths.config_path(), paths.calib_path(), paths.activation_path()):
        assert os.path.dirname(yol) == str(tmp_path)


def test_veri_dosyalari_listesi():
    """G9 kurucu taramasi bu listeye dayanir — uc dosya da sayilmali."""
    assert set(paths.VERI_DOSYALARI) == {"config.json", "calib.json",
                                         "aktivasyon.dat"}


def test_mutlak_calib_yolu_oldugu_gibi_kalir(monkeypatch, tmp_path):
    mutlak = str(tmp_path / "baska" / "calib.json")
    monkeypatch.setenv(paths.VERI_KOKU_ENV, str(tmp_path))
    assert paths.calib_path(mutlak) == mutlak


# ---------------- ensure_seeded ----------------

def test_seed_veri_kokunu_olusturur(monkeypatch, tmp_path):
    hedef = tmp_path / "yeni"
    monkeypatch.setenv(paths.VERI_KOKU_ENV, str(hedef))
    paths.ensure_seeded()
    assert hedef.is_dir()


def test_seed_config_tohumlar(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.VERI_KOKU_ENV, str(tmp_path))
    paths.ensure_seeded()
    assert os.path.isfile(paths.config_path())


def test_seed_calib_TOHUMLAMAZ(monkeypatch, tmp_path):
    """Baska salonun kalibrasyonu bu makinede yanlistir."""
    monkeypatch.setenv(paths.VERI_KOKU_ENV, str(tmp_path))
    paths.ensure_seeded()
    assert not os.path.exists(paths.calib_path())


def test_seed_aktivasyon_TOHUMLAMAZ(monkeypatch, tmp_path):
    """Tohumlanirsa dagitilan her kopya lisans kapisini bypass ederdi."""
    monkeypatch.setenv(paths.VERI_KOKU_ENV, str(tmp_path))
    paths.ensure_seeded()
    assert not os.path.exists(paths.activation_path())


def test_seed_mevcut_configi_EZMEZ(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.VERI_KOKU_ENV, str(tmp_path))
    hedef = tmp_path / "config.json"
    hedef.write_text('{"benim": "ayarim"}', encoding="utf-8")
    paths.ensure_seeded()
    assert hedef.read_text(encoding="utf-8") == '{"benim": "ayarim"}'


def test_seed_iki_kez_calisabilir(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.VERI_KOKU_ENV, str(tmp_path))
    paths.ensure_seeded()
    paths.ensure_seeded()
    assert os.path.isfile(paths.config_path())


def test_seed_yazilamayan_kokte_PATLAMAZ(monkeypatch, tmp_path):
    """Best-effort: tohumlama basarisiz olsa bile uygulama acilmali."""
    monkeypatch.setenv(paths.VERI_KOKU_ENV, str(tmp_path / "kok"))
    monkeypatch.setattr(paths.os, "makedirs",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("izin yok")))
    paths.ensure_seeded()   # raise etmemeli
