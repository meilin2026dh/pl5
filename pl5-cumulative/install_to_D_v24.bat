@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v24.ps1"
if errorlevel 1 (echo PL5 V2.4 installation failed. & pause & exit /b 1)
pause
