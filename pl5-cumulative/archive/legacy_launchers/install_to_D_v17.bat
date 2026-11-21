@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v17.ps1"
if errorlevel 1 (echo 安装失败，原有目录未强制覆盖。 & pause & exit /b 1)
echo 安装完成，请运行验证_V17.ps1。
pause
