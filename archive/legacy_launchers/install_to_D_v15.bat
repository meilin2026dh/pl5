@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v15.ps1" %*
if errorlevel 1 (
  echo PL5 V1.5 installation failed. Previous project folders were preserved.
  pause
  exit /b 1
)
pause
