#!/bin/bash
# ============================================================
#  Matematik Avi — oyunu baslat (Finder'da cift tikla)
#  Matematik-Avi-Baslat.bat'in macOS esdegeri.
# ============================================================
#  Tek giris noktasi: matematik.py (statik sunucu + tarayici +
#  dedektor). Cikis: ESC (tarayici kapanir, arka surecler de durur).
#
#  Secenekler (komut satirindan, bu dosyaya arguman olarak):
#    --pencere      tam ekran yerine pencere
#    --tarayicisiz  tarayiciyi acma (dedektor + sunucu tek basina)
#    --onizleme     dedektor onizleme penceresini goster
#    --kalibrasyon  kalibrasyon modunda ac (4 kose)
#    --http-port N  statik sunucu portu (varsayilan matematik.py'de)
# ============================================================
cd "$(dirname "$0")"

if [ -x ".venv/bin/python3" ]; then
  ".venv/bin/python3" matematik.py "$@"
else
  python3 matematik.py "$@"
fi
DURUM=$?

if [ $DURUM -ne 0 ]; then
  echo ""
  echo "Uygulama hata ile kapandi (kod: $DURUM). Bu pencereyi inceleyip kapatabilirsiniz."
  read -n 1 -s -r -p "Kapatmak icin bir tusa basin..."
  echo ""
fi
