#!/usr/bin/env python3
"""Matematik Avı'yı tek bir çalıştırılabilir pakete derler (Nuitka).

    python build.py                 # standalone klasör (varsayılan)
    python build.py --onefile       # tek dosya (yavaş açılır, bkz. aşağıda)
    python build.py --check         # sadece ön kontrolleri çalıştır
    python build.py --obfuscate-yok # JS obfuscation adımını atla
    python build.py --kurucu        # mevcut dist'ten Inno Setup kurucusu + ZIP + SHA

LİSANS HATTI (docs/plans/2026-09-12-lisans-ve-kurucu-entegrasyonu.md, G8/G9)
------------------------------------------------------------------------
Matematik Avı'nın asıl oyun mantığı Python'da değil — soru havuzu, tuzak
üretimi ve tur akışı `web/js/*.js` içinde. Ham konursa EXE'nin yanında
okunabilir kaynak olarak dururdu. Onun yerine önce `dist/web-hazir/`'a
kopyalanıp obfuscate edilir, sonra Lisans Merkezi'nin içerik anahtarıyla
`dist/web.pak`'e şifrelenir ve EXE'ye o girer. `matematik.py` lisans
kapısından geçince paketi BELLEKTE çözer; `tools/serve.py` bellekten servis
eder. Ham giren tek şey lisans ekranı (`lisans_web/`) — o, paket çözülmeden
önce gösterilmek zorunda.

NEDEN NUITKA, PyInstaller DEĞİL
-------------------------------
PyInstaller'ın ürettiği EXE bir arşivdir: `pyinstxtractor` + bir decompiler ile
kaynak kodun tamamı dakikalar içinde çıkarılır. Nuitka Python'u C'ye derleyip
makine kodu ürettiği için decompile edilemez.

NEDEN --standalone, --onefile DEĞİL (varsayılan)
------------------------------------------------
Onefile her açılışta kendini geçici bir dizine çıkarır: açılış saniyeler uzar
ve antivirüs yanlış pozitifi belirgin biçimde artar. Sergi PC'sinde açılış
hızı, demo alıcısında antivirüs önemlidir.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import surum  # noqa: E402
import paths  # noqa: E402

EXE_ADI = f"{surum.URUN_ADI}.exe"
DIST_ADI = "matematik.dist"

# Icerik anahtarinin durdugu yer. Lisans Merkezi ile AYNI depo; anahtar orada
# uretilir, burada yalnizca OKUNUR.
DEPO_ENV = "LUDEN_LISANS"
DEPO_KLASORU = ".luden-lisans"

# Kurucuya (dist\*) SIZMAMASI gereken adlar. `paths.VERI_DOSYALARI` (config.json,
# calib.json, aktivasyon.dat) TEK KAYNAK — burada TEKRARLANMAZ. Bu ikisi
# yazilabilir veri kokune ait, standalone dist'e asla girmemeli; girmisse
# birisi SPRAY-benzeri bir test sirasinda MATEMATIK_VERI_KOKU=dist ile
# calistirip unutmustur.
DIST_YASAK = paths.VERI_DOSYALARI + ("lisanslar.json",)
DIST_YASAK_UZANTI = (".key",)

MODEL_REL = os.path.join("python", "models", paths.MODEL_ADI)
CONFIG_ORNEK_REL = os.path.join("python", "config.json")

# Dedektor (main, net, camera, detection, gesture, mapping, selection,
# smoothing, config) python/ altinda, kokte DEGIL. `matematik.py` bu klasoru
# calisma aninda sys.path'e ekliyor (satir 31-33) ama Nuitka statik analiz
# yapar: o satirlar derleme sirasinda CALISMAZ. PYTHONPATH ile ayni yolu
# derleyiciye de vermezsek Nuitka "failed to locate module 'net.ws_sender'"
# deyip durur — ya da o bayrak kaldirilirsa sessizce dedektorsuz bir EXE
# uretir (kamera hic acilmaz, traceback yok).
PY_DIR = os.path.join(ROOT, "python")

# Sadece JS'i obfuscate ederiz; fontlar (.woff2) zaten ikili/minify.
WEB_JS_KOK = "js"


def preflight(strict: bool = True) -> bool:
    """Paketlenecek her şey yerinde mi? Eksikse ne yapılacağını söyle."""
    model = os.path.join(ROOT, MODEL_REL)
    if not os.path.isfile(model):
        print(f"[build] EKSIK: {MODEL_REL}")
        print("        Bu model el takibi icin gerekli ve internetsiz bir demo "
              "makinesinde\n        gomulmezse el takibi hic calismaz. Once "
              "`cd python && python download_model.py` ile\n        indirin, "
              "sonra build'i tekrar calistirin.")
        if strict:
            return False
    return True


# Native ikili tasiyan paketler. Nuitka bunlarin .dll/.pyd dosyalarini
# GUVENILIR sekilde bulamaz: ctypes ile calisma zamaninda yuklendikleri icin
# import analizinde gorunmezler ve --include-package-data DLL'leri kapsamaz.
NATIVE_PACKAGES = ("mediapipe", "cv2")
NATIVE_SUFFIXES = (".dll", ".pyd", ".so")


def _site_packages() -> str:
    import sysconfig
    return sysconfig.get_paths()["purelib"]


def _mediapipe_dll() -> Path:
    """libmediapipe.dll'in konumu paketten TURETILIR, hardcode edilmez.

    G0 spike'inde bulunan zorunlu bayrak: mediapipe 0.10.35'te tasks motoru
    bir .pyd degil, ctypes ile yuklenen bir C kutuphanesi. Statik analiz
    goremiyor ve --include-package-data DLL almiyor.
    """
    import mediapipe
    return Path(mediapipe.__file__).parent / "tasks" / "c" / "libmediapipe.dll"


def copy_missing_natives(dist_dir: str) -> int:
    """Nuitka'nin atladigi native ikilileri pakete kopyalar. Kopyalanan sayisi doner."""
    site = _site_packages()
    copied = 0
    for pkg in NATIVE_PACKAGES:
        src_root = os.path.join(site, pkg)
        if not os.path.isdir(src_root):
            continue
        for root, _dirs, files in os.walk(src_root):
            for name in files:
                if not name.lower().endswith(NATIVE_SUFFIXES):
                    continue
                rel = os.path.relpath(os.path.join(root, name), site)
                dest = os.path.join(dist_dir, rel)
                if os.path.isfile(dest):
                    continue
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(os.path.join(root, name), dest)
                print(f"[build] native eklendi: {rel}")
                copied += 1
    return copied


def verify_dist(dist_dir: str) -> bool:
    """Paket gercekten calisabilir mi? Eksikse SESSIZ bir bozukluk olurdu."""
    ok = True
    required = [
        (EXE_ADI, "calistirilabilir"),
        ("web.pak", "sifreli kiosk arayuzu"),
        (os.path.join("lisans_web", "index.html"), "lisans ekrani"),
        ("config.ornek.json", "ilk calistirma tohumlama sablonu"),
        (os.path.join("models", paths.MODEL_ADI), "el takibi modeli"),
        (os.path.join("mediapipe", "tasks", "c", "libmediapipe.dll"), "el takibi"),
    ]
    for rel, what in required:
        if not os.path.isfile(os.path.join(dist_dir, rel)):
            print(f"[build] EKSIK ({what}): {rel}")
            ok = False

    # Ham web/ dist'e sizarsa web.pak bosunadir: oyunun tamami EXE'nin
    # yaninda okunabilir JS olarak dururdu.
    if os.path.isdir(os.path.join(dist_dir, "web")):
        print("[build] HAM web/ klasoru dist'te — web.pak anlamsiz. Dagitmayin.")
        ok = False
    return ok


def dist_yasaklari(dist_dir: str) -> list:
    """Kurucuya girmemesi gereken dosya/klasorlerin dist icindeki listesi."""
    bulunan = []
    for root, dirs, files in os.walk(dist_dir):
        for ad in list(dirs) + files:
            rel = os.path.relpath(os.path.join(root, ad), dist_dir)
            if ad in DIST_YASAK or ad.lower().endswith(DIST_YASAK_UZANTI):
                bulunan.append(rel)
        dirs[:] = [d for d in dirs if d not in DIST_YASAK]
    return bulunan


# ---------------------------------------------------------------------------
# Icerik paketi (web -> obfuscate -> web.pak)
# ---------------------------------------------------------------------------

def _depo_koku() -> Path:
    ozel = os.environ.get(DEPO_ENV)
    return Path(ozel) if ozel else Path.home() / DEPO_KLASORU


def icerik_anahtarini_oku() -> tuple:
    """(paket_no, 32 bayt anahtar) — Lisans Merkezi'nin deposundan.

    ANAHTAR BURADA URETILMEZ: uretilseydi her yeni build dagitilmis TUM
    lisanslari cope atardi.
    """
    import lisans

    yol = _depo_koku() / "urunler" / lisans.URUN / "icerik.key"
    if not yol.exists():
        raise SystemExit(
            f"[build] icerik anahtari yok: {yol}\n"
            "Lisans Merkezi'ni acip bu urun icin anahtar uretin "
            "(01-Projects/LisansMerkezi -> MERKEZ.bat).")
    veri = json.loads(yol.read_text(encoding="utf-8"))
    return int(veri["paket_no"]), base64.b64decode(veri["anahtar"])


def obfuscator_komutu(girdi: Path, cikti: Path) -> list:
    """javascript-obfuscator cagrisi — ES MODUL UYUMLU, muhafazakar ayarlar.

    rename-globals ACIK olsaydi export edilen adlar degisir, import'lar
    sessizce kirilirdi (kiosk bos ekran acardi).
    """
    npx = shutil.which("npx") or "npx"
    return [npx, "--yes", "javascript-obfuscator", str(girdi),
            "--output", str(cikti),
            "--compact", "true",
            "--rename-globals", "false",
            "--control-flow-flattening", "false",
            "--string-array", "true",
            "--string-array-encoding", "base64"]


def web_hazirla(obfuscate: bool = True) -> Path:
    """web/ -> (obfuscate) -> tek sifreli paket. Donen deger dist/web.pak."""
    import web_paket

    dist = Path(ROOT) / "dist"
    hazir = dist / "web-hazir"
    if hazir.exists():
        shutil.rmtree(hazir)
    dist.mkdir(parents=True, exist_ok=True)
    shutil.copytree(Path(ROOT) / "web", hazir)

    if not obfuscate:
        print("[build] obfuscation ATLANDI (--obfuscate-yok)")
    else:
        sayac = 0
        for js in sorted((hazir / WEB_JS_KOK).rglob("*.js")):
            sonuc = subprocess.run(obfuscator_komutu(js, js), cwd=ROOT,
                                   capture_output=True, text=True,
                                   encoding="utf-8", errors="replace")
            if sonuc.returncode != 0:
                raise SystemExit(
                    f"[build] obfuscation basarisiz ({js.name}):\n"
                    f"{sonuc.stderr.strip()}\n"
                    "node/npx kurulu mu? Gecici cozum: --obfuscate-yok")
            sayac += 1
        print(f"[build] {sayac} JS dosyasi obfuscate edildi")

    paket_no, anahtar = icerik_anahtarini_oku()
    pak = dist / "web.pak"
    pak.write_bytes(web_paket.paketle(hazir, anahtar, paket_no))
    shutil.rmtree(hazir)
    print(f"[build] web paketi: {pak.name} "
          f"({pak.stat().st_size / 1024:.0f} KB, sifreli, paket_no={paket_no})")
    return pak


# ---------------------------------------------------------------------------
# Kurucu (Inno Setup)
# ---------------------------------------------------------------------------

ISS_DOSYASI = os.path.join(ROOT, "installer", "MatematikAvi.iss")
INNO_KLASORU = "Inno Setup 6"


def iscc_adaylari() -> list:
    r"""ISCC.exe'nin bulunabilecegi yerler, olasilik sirasiyla.

    winget install JRSoftware.InnoSetup derleyiciyi Program Files'a DEGIL,
    kullanici basina %LOCALAPPDATA%\Programs altina koyuyor. Yollar ortam
    degiskenlerinden turetilir — surucu harfi elle yazilmaz.
    """
    kokler = [os.environ.get("LOCALAPPDATA", ""),
              os.environ.get("ProgramFiles(x86)", ""),
              os.environ.get("ProgramFiles", "")]
    adaylar = []
    for kok in kokler:
        if not kok:
            continue
        adaylar.append(Path(kok) / "Programs" / INNO_KLASORU / "ISCC.exe")
        adaylar.append(Path(kok) / INNO_KLASORU / "ISCC.exe")
    return adaylar


def iscc_yolu():
    """ISCC.exe nerede? Once ISCC ortam degiskeni, sonra PATH, sonra adaylar."""
    ozel = os.environ.get("ISCC")
    if ozel and Path(ozel).exists():
        return Path(ozel)
    bulunan = shutil.which("ISCC")
    if bulunan:
        return Path(bulunan)
    for aday in iscc_adaylari():
        if aday.exists():
            return aday
    return None


def sha256(yol) -> str:
    ozet = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            ozet.update(parca)
    return ozet.hexdigest()


def kurucu_uret(dist_dir: str) -> int:
    """build/matematik.dist -> (temizlik taramasi) -> kurucu -> ZIP -> SHA-256."""
    exe = os.path.join(dist_dir, EXE_ADI)
    if not os.path.isfile(exe):
        print(f"[kurucu] {exe} yok — once `python build.py` calistir.")
        return 1

    yasak = dist_yasaklari(dist_dir)
    if yasak:
        print("[kurucu] dist'te kurucuya GIRMEMESI gereken dosyalar var:")
        for rel in yasak:
            print("         - " + rel)
        print("         Temizleyip yeniden deneyin (build/ silinip yeniden derlenebilir).")
        return 1

    iscc = iscc_yolu()
    if iscc is None:
        print("[kurucu] ISCC.exe bulunamadi. Inno Setup 6 kurulu degil.")
        print("         Kurulum:  winget install JRSoftware.InnoSetup")
        print(r"         Baska yere kurulduysa:  set ISCC=<tam yol>\ISCC.exe")
        return 1

    komut = [str(iscc),
             f"/DSURUM={surum.SURUM}",
             f"/DURUN={surum.URUN_ADI}",
             f"/DKURUCU_ADI={surum.KURUCU_ADI}",
             ISS_DOSYASI]
    print("[kurucu] " + " ".join(komut))
    kod = subprocess.call(komut, cwd=ROOT)
    if kod != 0:
        print(f"[kurucu] ISCC basarisiz (cikis {kod})")
        return kod

    setup = Path(ROOT) / "dist" / f"{surum.KURUCU_ADI}.exe"
    if not setup.exists():
        print(f"[kurucu] ISCC bitti ama {setup} yok.")
        return 1

    zip_yolu = setup.with_suffix(".zip")
    with zipfile.ZipFile(zip_yolu, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(setup, arcname=setup.name)
        kilavuz = Path(ROOT) / "docs" / "KURULUM.md"
        if kilavuz.exists():
            z.write(kilavuz, arcname="KURULUM.txt")
        else:
            print(f"[kurucu] UYARI: {kilavuz} yok — ZIP kilavuzsuz gidiyor.")

    mb = zip_yolu.stat().st_size / (1024 * 1024)
    print(f"\n[kurucu] TAMAM  {zip_yolu}  ({mb:.1f} MB)")
    print(f"[kurucu] SHA-256: {sha256(zip_yolu)}")
    print("[kurucu] Bu ozeti indirme sayfasinda/e-postada yayinla — "
          "kullanici dosyayi dogrulayabilsin.")
    return 0


def nuitka_env() -> dict:
    """Nuitka'nin modul arama yolu = calistiran yorumlayicinin sys.path'i.

    PY_DIR'i PYTHONPATH'e koyarak derleyiciye `matematik.py`'nin calisma
    aninda kurdugu yolun aynisini veriyoruz. Mevcut PYTHONPATH korunur.
    """
    env = dict(os.environ)
    onceki = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = PY_DIR + (os.pathsep + onceki if onceki else "")
    return env


def nuitka_command(onefile: bool, output_dir: str) -> list:
    """Nuitka komut satırı. Native bagimliliklarin her biri bilerek listelendi."""
    cmd = [
        sys.executable, "-m", "nuitka",
        "--assume-yes-for-downloads",
        "--onefile" if onefile else "--standalone",
        # Konsol penceresi olmasin: alici cift tiklayinca siyah bir pencere
        # degil oyunu gormeli. `matematik._olumcul` acilis hatalarini bir
        # Windows mesaj kutusuyla soyler.
        "--windows-console-mode=disable",
        # mediapipe matplotlib'i suruklyor, o da bir GUI toolkit secimi
        # bekliyor. Bize gerekmiyor (tum arayuz tarayicida).
        "--enable-plugin=no-qt",
        # --- Windows kaynak damgasi (tek kaynak: surum.py) ---
        f"--company-name={surum.SIRKET}",
        f"--product-name={surum.URUN_ADI}",
        f"--product-version={surum.SURUM}",
        f"--file-version={surum.DOSYA_SURUMU}",
        f"--file-description={surum.URUN_ADI} — el hareketiyle matematik sergisi",
        f"--copyright={surum.SIRKET}",
        # Kiosk arayuzu HAM GIRMEZ: web_hazirla() tek sifreli paket uretir,
        # matematik.py onu bellekte cozer.
        f"--include-data-files={os.path.join(ROOT, 'dist', 'web.pak')}=web.pak",
        # Lisans ekrani HAM girer: web.pak sifreliyse "lisans gir" ekrani
        # lisans olmadan acilamazdi.
        f"--include-data-dir={os.path.join(ROOT, 'lisans_web')}=lisans_web",
        # Ilk calistirmada data_root()'a tohumlanan sablon. AD BILEREK
        # config.json DEGIL: VERI_DOSYALARI (paths.py) o adi kurucuya asla
        # girmemesi gereken dosyalar arasinda sayiyor.
        f"--include-data-files={os.path.join(ROOT, CONFIG_ORNEK_REL)}=config.ornek.json",
        # Lisans katmani matematik.py'de fonksiyon icinde (tembel) import
        # ediliyor; acikca listele ki biri lazy import'u tasidiginda EXE'de
        # "No module named lisans" cikmasin.
        "--include-module=lisans",
        "--include-module=lisans_bicim",
        "--include-module=lisans_durum",
        "--include-module=lisans_ekrani",
        "--include-module=parmak_izi",
        "--include-module=web_paket",
        "--include-module=surum",
        "--include-module=paths",
        "--include-package=cryptography",
        # Dedektorun govdesi (python/main.py) matematik.py'de fonksiyon icinde
        # `import main as dedektor` diye cagriliyor. PYTHONPATH olmadan bu ad
        # derleme aninda hic cozulemez; oldugunda da lazy import'un takip
        # edildigine guvenmek yerine acikca listeliyoruz.
        "--include-module=main",
        # net.ws_sender G0 spike'inde acikca listelendi: gorunurde gereksiz
        # (net/__init__.py onu ustte import ediyor, Nuitka zaten takip eder)
        # ama testle kilitlenebilir bir sozlesme olsun diye acik tutuluyor.
        "--include-module=net.ws_sender",
        # ZORUNLU (G0): websockets 14+ kendi alt paketini (asyncio.server)
        # lazy_import ile cozuyor. Bayraksiz belirti YOK: derleme yesil,
        # EXE calisir GORUNUR ama WS portu hic acilmaz — tarayici bos ekran
        # acar. Traceback yok, sessizce bozulur.
        "--include-package=websockets",
        # mediapipe ve cv2 veri/protobuf dosyalarini dinamik yukluyor;
        # --include-package-data DLL almadigi icin libmediapipe.dll AYRICA
        # elle eklenir (asagida).
        "--include-package-data=mediapipe",
        "--include-package-data=cv2",
        # NOT: pywebview icin --include-package VERILMEZ. Nuitka'nin
        # pywebview eklentisi platform arka ucunu kendisi secer; elle
        # eklemek "Conflict between user and plugin decision" hatasi verir
        # (KimyaLab/SprayTarih build'inde olculdu).
        f"--output-filename={EXE_ADI}",
        f"--output-dir={output_dir}",
    ]

    dll = _mediapipe_dll()
    if dll.is_file():
        cmd.append(f"--include-data-files={dll}="
                   "mediapipe/tasks/c/libmediapipe.dll")

    model = os.path.join(ROOT, MODEL_REL)
    if os.path.isfile(model):
        cmd.append(f"--include-data-files={model}="
                   f"models/{paths.MODEL_ADI}")

    cmd.append(os.path.join(ROOT, "matematik.py"))
    return cmd


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Matematik Avi EXE build")
    parser.add_argument("--onefile", action="store_true",
                        help="tek dosya uret (yavas acilir, antivirus riski yuksek)")
    parser.add_argument("--check", action="store_true",
                        help="sadece on kontrolleri calistir, derleme yapma")
    parser.add_argument("--out", default=os.path.join(ROOT, "build"),
                        help="cikti dizini (varsayilan: build/)")
    parser.add_argument("--force", action="store_true",
                        help="model eksik olsa bile derle (el takibi calismaz)")
    parser.add_argument("--obfuscate-yok", action="store_true",
                        help="JS obfuscation adimini atla")
    parser.add_argument("--kurucu", action="store_true",
                        help="derlemeyi atla; mevcut build/matematik.dist'ten "
                             "Inno Setup kurucusu + ZIP + SHA-256 uret")
    args = parser.parse_args(argv)

    # cp1254 TUZAGI: Turkce Windows'ta stdout cp1254'tur, Nuitka ciktisindaki
    # bazi karakterler orada kodlanamaz; derleme degil YAZDIRMA hatasiyla durur.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:      # noqa: BLE001
        pass

    if args.kurucu:
        return kurucu_uret(os.path.join(args.out, DIST_ADI))

    if not preflight(strict=not args.force):
        print("\n[build] Durduruldu. Modeli tamamlayin veya --force kullanin.")
        return 1
    if args.check:
        print("[build] On kontroller tamam.")
        return 0

    try:
        import nuitka  # noqa: F401
    except ImportError:
        print("[build] Nuitka kurulu degil. Kurmak icin:\n"
              "        .venv\\Scripts\\python.exe -m pip install nuitka")
        return 1

    if shutil.which("cl") is None and os.name == "nt":
        print("[build] NOT: MSVC bulunamadi. Nuitka gerekirse MinGW64'u kendisi"
              " indirecek (--assume-yes-for-downloads).")

    # Paket ONCE hazirlanmali: nuitka_command uretilecek dosyaya isaret ediyor.
    web_hazirla(obfuscate=not args.obfuscate_yok)

    cmd = nuitka_command(args.onefile, args.out)
    print("[build] " + " ".join(cmd) + "\n")
    print("[build] Ilk derleme 10+ dakika surebilir.\n")
    rc = subprocess.call(cmd, cwd=ROOT, env=nuitka_env())
    if rc != 0:
        return rc

    if args.onefile:
        print("[build] NOT: --onefile'da native ikili tamamlama YAPILAMAZ "
              "(tek dosya sonradan degistirilemez). Standalone kullanin.")
        return rc

    dist = os.path.join(args.out, DIST_ADI)
    copied = copy_missing_natives(dist)
    print(f"[build] {copied} native dosya tamamlandi.")
    if not verify_dist(dist):
        print("\n[build] Paket EKSIK. Dagitmayin.")
        return 1
    print(f"\n[build] Hazir: {os.path.join(dist, EXE_ADI)}")
    print("        Kurucu icin:  python build.py --kurucu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
