@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v18.ps1"
if errorlevel 1 (echo Installation failed. & pause & exit /b 1)
pause
