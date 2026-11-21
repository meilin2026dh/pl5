@echo off
chcp 65001 > nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v27.ps1"
if errorlevel 1 (echo V2.7 install failed. & pause & exit /b 1)
echo V2.7 install completed.
pause
