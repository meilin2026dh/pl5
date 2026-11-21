@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v28.ps1"
if errorlevel 1 (echo 安装失败。请阅读屏幕上方原因。& pause & exit /b 1)
pause
