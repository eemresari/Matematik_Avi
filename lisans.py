"""Matematik Avi'nin lisans kapisi: urune ozel sabitler + dogrulama.

Bicimin kendisi lisans_bicim.py'dedir — o dosya Lisans Merkezi'nden BIREBIR
kopyalanir ve URUNE OZEL HICBIR SABIT TASIMAZ. Urune ozel olan her sey burada
durur; boylece kopya ayrismaz. (Ayrisirsa dagitilmis keyler dogrulanamaz hale
gelir ve bunu ilk musteri fark eder.)

EXE'DE YALNIZ ACIK ANAHTAR VARDIR: imzayi dogrulayabilir, URETEMEZ. Ozel
anahtar Lisans Merkezi'nin calistigi makinededir, bu depoda degil. Oyunun
icinde HIC key yoktur — EXE'yi parcalayan biri tek bir key cikaramaz.
"""

from __future__ import annotations

import lisans_bicim

URUN = "matematik"

# Icerik anahtarinin surumu. Rotasyon gerekirse artirilir; eski lisanslar
# "eski surum icin uretilmis" mesajiyla reddedilir.
PAKET_NO = 1

# Ed25519 acik anahtar (32 bayt, hex). SIR DEGILDIR, depoya girer.
# Lisans Merkezi'ndeki "matematik" cifti uretilirken yazdirilir (MERKEZ.bat ->
# Matematik Avi -> "Anahtar cifti uret"). YER TUTUCU KALDIGI SURECE hicbir
# gercek anahtar dogrulanamaz; tests/test_lisans.py bunu kilitler.
# (2026-09-13 dolduruldu; ~/.luden-lisans/urunler/matematik/acik.key ile ayni.)
ACIK_ANAHTAR_HEX = "d626e47e873b14df200799a3834f6a47492b48b60ecd3ea48f872a1dd6825466"

# Hatalari burada disa ac: cagiran taraf lisans_bicim'i import etmek zorunda
# kalmasin, tek kapi olsun.
LisansHatasi = lisans_bicim.LisansHatasi
ImzaHatasi = lisans_bicim.ImzaHatasi
UrunHatasi = lisans_bicim.UrunHatasi
SurumHatasi = lisans_bicim.SurumHatasi
SuresiGecmis = lisans_bicim.SuresiGecmis


def dogrula(metin: str, simdi: float = None) -> dict:
    """Lisans metnini Matematik Avi icin dogrula ve yuku don."""
    return lisans_bicim.dogrula(metin, ACIK_ANAHTAR_HEX, urun=URUN,
                                paket_no=PAKET_NO, simdi=simdi)
