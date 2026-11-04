@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v12.ps1"
if errorlevel 1 (
 echo V1.2部署遇到错误，请查看上方提示。
 pause
 exit /b 1
)
pause
