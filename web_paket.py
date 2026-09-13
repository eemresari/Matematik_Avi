"""web/ ağacını tek şifreli pakete koyar ve BELLEKTE çözer.

NEDEN: Nuitka Python tarafını makine koduna çevirir, ama Matematik Avı'nın asıl
oyunu Python'da değil — soru havuzu ve tuzak üretimi `web/js/questions.js`,
token alanı `tokens.js`, tur akışı `game.js` içinde. Ham konurlarsa EXE'nin
yanında okunabilir kaynak olarak dururlar; soruların düz metin durması serginin
kendisini kopyalanabilir kılar.

Biçim:  MAPAK1\\n | paket_no (4 bayt BE) | 12 bayt nonce | AES-256-GCM(zip)

paket_no BAŞLIKTA AÇIK DURUR: EXE, lisansı çözmeden önce "bu anahtar bu sürüm
için mi" diyebilmeli; yoksa sürüm uyuşmazlığında kullanıcıya "geçersiz anahtar"
gibi yanlış bir mesaj gösterirdi.

Zip ARA BİR ADIM: dosya adlarını ve içeriklerini tek blokta tutmanın en kısa
yolu. Şifreleme zip'in ÜSTÜNDE olduğu için pakette ne dosya adı ne de içerik
düz metin görünür.

ANAHTAR BU MODÜLDE YOK: çağıran taraf onu lisansın imzalı yükünden getirir.
Böylece "anahtarsız oyun açılmaz" yamalanabilir bir kontrol değil, kriptografik
bir gerçektir — yamalanacak dallanma yoktur.
"""

from __future__ import annotations

import io
import secrets
import zipfile
from pathlib import Path

BASLIK = b"MAPAK1\n"
PAKET_NO_UZUNLUK = 4
NONCE_UZUNLUK = 12
_ON_EK = len(BASLIK) + PAKET_NO_UZUNLUK


def paketle(kok: Path, anahtar: bytes, paket_no: int) -> bytes:
    """kok altındaki TÜM dosyaları tek şifreli bloğa koy."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(Path(kok).rglob("*")):
            if p.is_file():
                # as_posix(): tarayıcı '/' ile ister; Windows'ta '\' yazılırsa
                # paket açılır ama her istek 404 döner.
                z.writestr(p.relative_to(kok).as_posix(), p.read_bytes())
    nonce = secrets.token_bytes(NONCE_UZUNLUK)
    govde = AESGCM(anahtar).encrypt(nonce, tampon.getvalue(), None)
    return BASLIK + paket_no.to_bytes(PAKET_NO_UZUNLUK, "big") + nonce + govde


def paket_no_oku(veri: bytes) -> int:
    """Şifreyi ÇÖZMEDEN paket sürümünü oku."""
    if not veri.startswith(BASLIK) or len(veri) < _ON_EK:
        raise ValueError("Bu bir Matematik Avi web paketi degil (baslik uymuyor).")
    return int.from_bytes(veri[len(BASLIK):_ON_EK], "big")


def coz(veri: bytes, anahtar: bytes) -> dict:
    """Paketi BELLEKTE çöz. Diske hiçbir şey yazılmaz."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    paket_no_oku(veri)      # başlık doğrulaması
    kalan = veri[_ON_EK:]
    nonce, gizli = kalan[:NONCE_UZUNLUK], kalan[NONCE_UZUNLUK:]
    duz = AESGCM(anahtar).decrypt(nonce, gizli, None)
    with zipfile.ZipFile(io.BytesIO(duz)) as z:
        return {ad: z.read(ad) for ad in z.namelist()}
