"""Urun kimligi ve surum numarasi — TEK KAYNAK.

Surum bilgisi uc yerde birden gorunur:
    1. EXE'nin Windows ozellikleri (Nuitka --product-version / --file-version)
    2. Kurucu dosya adi ve "Program Ekle/Kaldir" kaydi (Inno Setup)
    3. Teslim ZIP'inin adi
Ucu de burayi okur. Elle uc yerde guncellemek, birinde unutmak demekti:
musteriye "0.9.0" yazan bir kurucudan "0.8.0" damgali EXE cikardi.

SURUM ARTIRMA: ilk gercek musteri teslimi 1.0.0'dir. 0.9.x, teslim oncesi
kendi test kurulumlarini isaretler.
"""

from __future__ import annotations

SURUM = "0.9.0"
URUN_ADI = "Matematik Avi"      # ASCII: Windows kaynak tablosu + ISCC cp1254
SIRKET = "Luden Studio"

# Windows kaynak tablosu 4 haneli sayisal surum ister (a.b.c.d). SURUM'un
# uc hanesine build hanesi olarak 0 eklenir; ayri bir sabit tutulmaz ki
# ikisi ayrisamasin.
DOSYA_SURUMU = SURUM + ".0"

# Kurucu ciktisinin adi. URUN_ADI'ndan TURETILMEZ: uzerinde bosluk var
# (Windows ozellikleri/Inno gorunumu icin dogru), ama dosya adi bosluksuz
# olmali (paths.UYGULAMA_ADI = "MatematikAvi" ile ayni desen).
KURUCU_ADI = f"MatematikAvi-Setup-{SURUM}-win64"
