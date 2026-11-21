@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v29.ps1"
if errorlevel 1 (
  echo 安装失败；请阅读终端错误并检查D盘空间。
  pause
  exit /b 1
)
pause
