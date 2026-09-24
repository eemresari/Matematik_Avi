#!/bin/bash
# ============================================================
#  Matematik Avi — kamera ayar penceresi (kamera sec + onizle + kaydet)
#  Kamera-Ayarlari.bat'in macOS esdegeri.
# ============================================================
cd "$(dirname "$0")"

if [ -x ".venv/bin/python3" ]; then
  PYRUN="$(pwd)/.venv/bin/python3"
else
  PYRUN="python3"
fi

cd "python" || exit 1

if ! "$PYRUN" -c "import sys" >/dev/null 2>&1; then
  echo ""
  echo "[HATA] Bu bilgisayarda Python 3 bulunamadi."
  echo "Once Python 3 kurun: https://www.python.org/downloads/"
  echo "Sonra bu klasordeki Kurulum.command dosyasina cift tiklayin."
  echo ""
  read -n 1 -s -r -p "Kapatmak icin bir tusa basin..."
  echo ""
  exit 1
fi

if ! "$PYRUN" -c "import cv2, PIL" >/dev/null 2>&1; then
  echo ""
  echo "[HATA] Gerekli Python paketleri eksik (opencv-python / Pillow)."
  echo "Bu klasordeki Kurulum.command dosyasina cift tiklayip paketleri kurun."
  echo ""
  read -n 1 -s -r -p "Kapatmak icin bir tusa basin..."
  echo ""
  exit 1
fi

"$PYRUN" camera_settings.py
DURUM=$?

if [ $DURUM -ne 0 ]; then
  echo ""
  echo "[HATA] Kamera ayar penceresi calisirken bir hata olustu (yukariya bakin)."
  echo ""
  read -n 1 -s -r -p "Kapatmak icin bir tusa basin..."
  echo ""
fi
exit $DURUM
