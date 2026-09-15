@echo off
REM Matematik Avi - cift tiklayinca kiosk modunu baslatir.
REM Tek giris noktasi: matematik.py (statik sunucu + tarayici + dedektor).
REM
REM Secenekler:  --pencere  --tarayicisiz  --onizleme  --kalibrasyon
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" matematik.py %*
) else (
  python matematik.py %*
)
if errorlevel 1 pause
