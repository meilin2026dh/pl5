@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v22.ps1"
if errorlevel 1 (echo Install failed. & pause & exit /b 1)
pause
