r"""Kurucu paketi kilitleri (standalone dist).

EXE yaninda yuzlerce DLL/.pyd var, `matematik.dist\*` recursesubdirs ile
girmek ZORUNDA. Kural: ISCC'den ONCE dist taranir; config.json, calib.json,
aktivasyon.dat (paths.VERI_DOSYALARI — yazilabilir veri kokune ait, standalone
dist'te ASLA olmamali), lisanslar.json ya da bir anahtar dosyasi (*.key)
bulunursa build durur.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

import build  # noqa: E402
import surum  # noqa: E402
import paths  # noqa: E402

ISS = KOK / "installer" / "MatematikAvi.iss"


def _iss_metni() -> str:
    return ISS.read_text(encoding="utf-8")


def _source_satirlari() -> list[str]:
    return [s.strip() for s in _iss_metni().splitlines()
            if s.strip().lower().startswith("source:")]


def test_iss_dosyasi_var():
    assert ISS.exists()


def test_tek_kaynak_satiri_ve_matematik_dist():
    satirlar = _source_satirlari()
    assert len(satirlar) == 1, satirlar
    assert r"..\build\matematik.dist\*" in satirlar[0], satirlar[0]
    assert "recursesubdirs" in satirlar[0]


def test_iss_diger_urunlerin_GUID_ini_kullanmiyor():
    """Kopyalanan .iss'te GUID kalirsa iki oyun Windows'ta AYNI program
    sayilir: biri digerini kaldirir/ustune yazar."""
    metin = _iss_metni()
    for baska_guid in ("1DC99EBF-CEA1-46E6-81BF-ECB8265A0FF6",   # KimyaLab
                       "D57F7590-27BB-4E79-A02D-54B9FE7DAFF8"):  # SprayTarih
        assert baska_guid not in metin
    assert re.search(r"AppId=\{\{[0-9A-F-]{36}\}", metin)
    kod = "\n".join(s for s in metin.splitlines() if not s.lstrip().startswith(";"))
    assert "KimyaLab" not in kod and "SprayTarih" not in kod


def test_iss_surumu_elle_yazmiyor():
    metin = _iss_metni()
    assert "AppVersion={#SURUM}" in metin
    assert "OutputBaseFilename={#KURUCU_ADI}" in metin
    setup_bolumu = metin.split("[Setup]", 1)[1].split("[", 1)[0]
    assert not re.search(r"=\s*\d+\.\d+\.\d+", setup_bolumu), setup_bolumu


def test_iss_urun_adini_disaridan_alir():
    metin = _iss_metni()
    assert "#ifndef URUN" in metin
    assert "{#URUN}.exe" in metin


def test_iss_kalibrasyon_kisayolu_var():
    """Kurulu EXE'nin yaninda Kalibrasyon.bat gitmez (kaynak-modu araci);
    --kalibrasyon'a Start Menu'den erisim kurucunun kendisi saglamali."""
    metin = _iss_metni()
    assert '--kalibrasyon' in metin


# --------------------------------------------------------------------------- #
# kurucu_uret akisi
# --------------------------------------------------------------------------- #

def _temiz_dist(tmp_path: Path) -> Path:
    d = tmp_path / "matematik.dist"
    d.mkdir()
    (d / build.EXE_ADI).write_bytes(b"MZ")
    (d / "web.pak").write_bytes(b"MAPAK1\n")
    (d / "python312.dll").write_bytes(b"x")
    return d


def test_kurucu_komutu_surum_urun_ad_gecirir(tmp_path, monkeypatch):
    yakalanan = []
    d = _temiz_dist(tmp_path)
    monkeypatch.setattr(build, "iscc_yolu", lambda: Path("ISCC.exe"))
    monkeypatch.setattr(build.subprocess, "call",
                        lambda komut, **k: yakalanan.append(komut) or 1)
    build.kurucu_uret(str(d))
    assert yakalanan, "ISCC hic cagrilmadi"
    komut = yakalanan[0]
    assert f"/DSURUM={surum.SURUM}" in komut
    assert f"/DURUN={surum.URUN_ADI}" in komut
    assert f"/DKURUCU_ADI={surum.KURUCU_ADI}" in komut
    assert komut[-1].endswith("MatematikAvi.iss")


def test_exe_yoksa_ISCC_aranmaz(tmp_path, monkeypatch):
    d = tmp_path / "matematik.dist"
    d.mkdir()
    monkeypatch.setattr(build, "iscc_yolu",
                        lambda: pytest.fail("EXE yokken ISCC aranmamali"))
    assert build.kurucu_uret(str(d)) == 1


@pytest.mark.parametrize("yasak", ["config.json", "calib.json",
                                   "aktivasyon.dat", "lisanslar.json",
                                   "ozel.key"])
def test_dist_te_yasak_DOSYA_varsa_build_DURUR(tmp_path, monkeypatch, yasak):
    d = _temiz_dist(tmp_path)
    (d / yasak).write_text("x", encoding="utf-8")
    monkeypatch.setattr(build, "iscc_yolu",
                        lambda: pytest.fail("yasak dosya varken ISCC cagrilmamali"))
    assert build.kurucu_uret(str(d)) == 1


def test_config_ornek_json_YASAK_DEGIL(tmp_path):
    """Sablon config.ornek.json mesru bir kaynak dosyasidir; VERI_DOSYALARI
    yalniz gercek 'config.json' adini yasakliyor."""
    d = _temiz_dist(tmp_path)
    (d / "config.ornek.json").write_text("{}", encoding="utf-8")
    assert build.dist_yasaklari(str(d)) == []


def test_yasak_tarama_alt_klasorlere_de_bakar(tmp_path):
    d = _temiz_dist(tmp_path)
    (d / "python").mkdir()
    (d / "python" / "aktivasyon.dat").write_text("x", encoding="utf-8")
    assert build.dist_yasaklari(str(d))


def test_temiz_dist_yasak_uretmez(tmp_path):
    assert build.dist_yasaklari(str(_temiz_dist(tmp_path))) == []


def test_yasak_liste_paths_VERI_DOSYALARI_ile_tutarli():
    """DIST_YASAK, paths.VERI_DOSYALARI'ni TEKRARLAMAZ — tek kaynak oradan."""
    assert set(paths.VERI_DOSYALARI) <= set(build.DIST_YASAK)


# --------------------------------------------------------------------------- #
# ISCC bulma
# --------------------------------------------------------------------------- #

def test_kullanici_basina_kurulum_da_taranir(monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Kullanici\AppData\Local")
    adaylar = [a.as_posix().lower() for a in build.iscc_adaylari()]
    assert any("appdata/local/programs/inno setup 6/iscc.exe" in a for a in adaylar)


def test_program_files_de_taranir(monkeypatch):
    monkeypatch.setenv("ProgramFiles(x86)", r"C:\Program Files (x86)")
    adaylar = [a.as_posix().lower() for a in build.iscc_adaylari()]
    assert any(a.endswith("program files (x86)/inno setup 6/iscc.exe") for a in adaylar)


def test_ISCC_ortam_degiskeni_her_seyi_EZER(monkeypatch, tmp_path):
    sahte = tmp_path / "ISCC.exe"
    sahte.write_text("", encoding="utf-8")
    monkeypatch.setenv("ISCC", str(sahte))
    assert build.iscc_yolu() == sahte


def test_adaylarda_SURUCU_HARFI_hardcode_YOK():
    import inspect
    kaynak = inspect.getsource(build.iscc_adaylari)
    govde = kaynak.split('"""')[-1]
    assert "C:" not in govde, govde


def test_zip_KURULUM_kilavuzunu_tasir():
    import inspect
    kaynak = inspect.getsource(build.kurucu_uret)
    assert "KURULUM.md" in kaynak and "KURULUM.txt" in kaynak
    assert (KOK / "docs" / "KURULUM.md").exists()


def test_KURULUM_kilavuzu_SMARTSCREEN_adimini_anlatiyor():
    metin = (KOK / "docs" / "KURULUM.md").read_text(encoding="utf-8")
    assert "Daha fazla bilgi" in metin
    assert "Yine de çalıştır" in metin
