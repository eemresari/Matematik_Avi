"""Build komutu ve surum damgasi kilitleri.

web/ HAM GIRMEZ: standalone dist'te EXE'nin yaninda okunabilir kaynak olarak
dururdu (soru havuzu, tuzak uretimi, tur akisi hep JS'te). Yerine sifreli
web.pak + ham lisans ekrani gider. Damga degerleri surum.py'den gelir.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

import build  # noqa: E402
import surum  # noqa: E402
import paths  # noqa: E402


def _komut() -> list[str]:
    return build.nuitka_command(False, str(KOK / "build"))


# --------------------------------------------------------------------------- #
# Ne girer, ne girmez
# --------------------------------------------------------------------------- #

def test_web_HAM_gomulmez():
    for p in _komut():
        if p.startswith("--include-data-dir="):
            assert "=web" not in p.replace("\\", "/").rstrip("/"), p


def test_web_pak_ve_lisans_ekrani_girer():
    komut = _komut()
    assert any(p.startswith("--include-data-files=") and p.endswith("=web.pak")
               for p in komut), komut
    assert any(p.startswith("--include-data-dir=") and p.endswith("=lisans_web")
               for p in komut), komut


def test_config_ornek_ADI_config_json_DEGIL():
    """VERI_DOSYALARI 'config.json'un kurucuya asla girmemesini sart kosuyor;
    sablon farkli bir adla (config.ornek.json) girmeli."""
    komut = _komut()
    assert any(p.endswith("=config.ornek.json") for p in komut), komut
    assert not any(p.endswith("=config.json") for p in komut), komut


@pytest.mark.parametrize("modul", ["lisans", "lisans_bicim", "lisans_durum",
                                   "lisans_ekrani", "parmak_izi", "web_paket",
                                   "surum", "paths"])
def test_tembel_import_edilen_lisans_modulleri_acikca_eklenir(modul):
    assert f"--include-module={modul}" in _komut()


def test_cryptography_paketi_eklenir():
    assert "--include-package=cryptography" in _komut()


def test_websockets_paketi_ZORUNLU_eklenir():
    """G0 spike: websockets 14+ lazy_import ile kendi alt paketini cozuyor.
    Bayraksiz belirti YOK — derleme yesil, EXE calisir GORUNUR, WS portu
    hic acilmaz. Bu yuzden en kritik bayrak budur."""
    assert "--include-package=websockets" in _komut()


def test_dedektor_modulu_acikca_eklenir():
    """python/main.py matematik.py'de fonksiyon icinde import ediliyor."""
    assert "--include-module=main" in _komut()


def test_PYTHONPATH_python_klasorunu_tasir():
    """Dedektor (main, net, camera, ...) python/ altinda, kokte degil.

    matematik.py o klasoru CALISMA ANINDA sys.path'e ekler; Nuitka ise statik
    analiz yapar. PYTHONPATH verilmezse derleme 'failed to locate module
    net.ws_sender' ile durur (11 Eylul'de oldu). Bayrak kaldirilirsa da EXE
    dedektorsuz cikar: kamera hic acilmaz, traceback yok.
    """
    env = build.nuitka_env()
    assert build.PY_DIR in env["PYTHONPATH"].split(os.pathsep)


def test_PYTHONPATH_mevcut_degeri_EZMEZ(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "/onceki/yol")
    parcalar = build.nuitka_env()["PYTHONPATH"].split(os.pathsep)
    assert build.PY_DIR in parcalar and "/onceki/yol" in parcalar


def test_mediapipe_cv2_paket_verisi_eklenir():
    komut = _komut()
    assert "--include-package-data=mediapipe" in komut
    assert "--include-package-data=cv2" in komut


def test_cikti_adi_dogru():
    assert "--output-filename=Matematik Avi.exe" in _komut()
    assert build.EXE_ADI == "Matematik Avi.exe"


def test_lisans_URETIM_modulleri_komutta_YOK():
    """Ozel anahtar EXE'ye girseydi her kopya lisans uretebilirdi."""
    for p in _komut():
        assert "lisans_uret" not in p and "imza_deposu" not in p, p


def test_webview_paketi_ELLE_EKLENMEZ():
    """Nuitka'nin pywebview eklentisi platform arka ucunu kendisi secer;
    elle --include-package=webview eklemek eklentiyle catisir (KimyaLab/
    SprayTarih build'inde 'Conflict between user and plugin decision' ile
    olculdu)."""
    for p in _komut():
        assert "webview" not in p, p


# --------------------------------------------------------------------------- #
# Surum damgasi
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("bayrak", ["--company-name", "--product-name",
                                    "--product-version", "--file-version"])
def test_exe_damgasi_bayraklari_var(bayrak):
    assert any(p.startswith(bayrak + "=") for p in _komut()), bayrak


def test_damga_degerleri_surum_modulunden():
    komut = _komut()
    assert f"--product-version={surum.SURUM}" in komut
    assert f"--file-version={surum.DOSYA_SURUMU}" in komut
    assert f"--company-name={surum.SIRKET}" in komut
    assert f"--product-name={surum.URUN_ADI}" in komut


def test_surum_bicimi():
    assert re.fullmatch(r"\d+\.\d+\.\d+", surum.SURUM), surum.SURUM
    assert re.fullmatch(r"\d+\.\d+\.\d+\.\d+", surum.DOSYA_SURUMU)
    assert surum.DOSYA_SURUMU.startswith(surum.SURUM + ".")
    assert surum.URUN_ADI == "Matematik Avi"
    assert surum.SURUM in surum.KURUCU_ADI
    assert surum.KURUCU_ADI.startswith("MatematikAvi")
    assert " " not in surum.KURUCU_ADI


# --------------------------------------------------------------------------- #
# verify_dist — standalone klasor
# --------------------------------------------------------------------------- #

def _sahte_dist(tmp_path: Path) -> Path:
    d = tmp_path / "matematik.dist"
    (d / "mediapipe" / "tasks" / "c").mkdir(parents=True)
    (d / "mediapipe" / "tasks" / "c" / "libmediapipe.dll").write_bytes(b"x")
    (d / "models").mkdir()
    (d / "models" / paths.MODEL_ADI).write_bytes(b"x")
    (d / "lisans_web").mkdir()
    (d / "lisans_web" / "index.html").write_text("x", encoding="utf-8")
    (d / build.EXE_ADI).write_bytes(b"MZ")
    (d / "web.pak").write_bytes(b"MAPAK1\n")
    (d / "config.ornek.json").write_text("{}", encoding="utf-8")
    return d


def test_verify_dist_tam_paket(tmp_path):
    assert build.verify_dist(str(_sahte_dist(tmp_path)))


def test_verify_dist_web_pak_yoksa_EKSIK(tmp_path):
    d = _sahte_dist(tmp_path)
    (d / "web.pak").unlink()
    assert not build.verify_dist(str(d))


def test_verify_dist_model_yoksa_EKSIK(tmp_path):
    d = _sahte_dist(tmp_path)
    (d / "models" / paths.MODEL_ADI).unlink()
    assert not build.verify_dist(str(d))


def test_verify_dist_ham_web_varsa_RED(tmp_path):
    d = _sahte_dist(tmp_path)
    (d / "web").mkdir()
    (d / "web" / "index.html").write_text("x", encoding="utf-8")
    assert not build.verify_dist(str(d))


# --------------------------------------------------------------------------- #
# Icerik anahtari depodan OKUNUR, uretilmez
# --------------------------------------------------------------------------- #

def test_icerik_anahtari_depodan_okunur(tmp_path, monkeypatch):
    import base64
    import json
    depo = tmp_path / "depo"
    (depo / "urunler" / "matematik").mkdir(parents=True)
    (depo / "urunler" / "matematik" / "icerik.key").write_text(json.dumps(
        {"paket_no": 1, "anahtar": base64.b64encode(b"q" * 32).decode()}),
        encoding="utf-8")
    monkeypatch.setenv("LUDEN_LISANS", str(depo))
    assert build.icerik_anahtarini_oku() == (1, b"q" * 32)


def test_icerik_anahtari_yoksa_build_DURUR(tmp_path, monkeypatch):
    monkeypatch.setenv("LUDEN_LISANS", str(tmp_path))
    with pytest.raises(SystemExit, match="icerik anahtari"):
        build.icerik_anahtarini_oku()


def test_obfuscator_ES_MODUL_uyumlu():
    k = build.obfuscator_komutu(Path("a.js"), Path("b.js"))
    i = k.index("--rename-globals")
    assert k[i + 1] == "false"
    i = k.index("--control-flow-flattening")
    assert k[i + 1] == "false"


def test_stdout_utf8_yeniden_yapilandirilir():
    """cp1254 konsolda Nuitka ciktisi UnicodeEncodeError ile build'i
    durduruyordu (KimyaLab'da olculdu)."""
    import inspect
    assert "reconfigure" in inspect.getsource(build.main)


def test_mediapipe_dll_yolu_HARDCODE_DEGIL():
    import inspect
    kaynak = inspect.getsource(build._mediapipe_dll)
    assert "C:" not in kaynak
    assert "mediapipe.__file__" in kaynak
