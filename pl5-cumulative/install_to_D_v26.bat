@echo off
chcp 65001 > nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v26.ps1"
if errorlevel 1 (echo 安装失败，请查看错误信息 & pause & exit /b 1)
echo 安装完成。
pause
