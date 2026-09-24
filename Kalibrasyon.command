#!/bin/bash
# ============================================================
#  Matematik Avi — Kalibrasyon. Kalibrasyon.bat'in macOS esdegeri.
#  Projeksiyon + kamera yerlestikten sonra bir kez calistir.
#  Tam ekran hedefler cikar; oyuncu yerinde durup imleci her
#  hedefe getirip sabit tutar.
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

if ! "$PYRUN" -c "import cv2, mediapipe" >/dev/null 2>&1; then
  echo ""
  echo "[HATA] Gerekli Python paketleri eksik (opencv-python / mediapipe)."
  echo "Bu klasordeki Kurulum.command dosyasina cift tiklayip paketleri kurun."
  echo ""
  read -n 1 -s -r -p "Kapatmak icin bir tusa basin..."
  echo ""
  exit 1
fi

echo ""
echo "Kalibrasyon basliyor. Pencereyi PROJEKSIYON ekranina tasiyin (gerekirse)."
echo "Oyuncu yerinde dursun; imleci her hedefe getirip ~1.5 sn sabit tutsun."
echo "SPACE: yakala   B: geri   R: bastan   A: kaydet   ESC: iptal"
echo ""
"$PYRUN" main.py --calibrate
DURUM=$?

if [ $DURUM -ne 0 ]; then
  echo ""
  echo "[HATA] Kalibrasyon calisirken bir hata olustu (yukariya bakin)."
  echo ""
  read -n 1 -s -r -p "Kapatmak icin bir tusa basin..."
  echo ""
fi
exit $DURUM
