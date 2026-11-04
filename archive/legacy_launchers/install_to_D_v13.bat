@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v13.ps1"
if errorlevel 1 (
 echo V1.3部署失败，请阅读终端错误提示。
 pause
 exit /b 1
)
pause
