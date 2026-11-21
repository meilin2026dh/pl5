@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v33.ps1"
if errorlevel 1 (echo Installation FAILED. & pause & exit /b 1)
echo V3.3 source deployed. Please run 验证_V33.ps1 in PowerShell.
pause
