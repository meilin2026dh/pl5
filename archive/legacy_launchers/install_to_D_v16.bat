@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v16.ps1"
if errorlevel 1 (
  echo 安装失败；请检查日志，之前版本和数据不会被主动删除。
  pause
  exit /b 1
)
echo 请继续运行 验证_V16.ps1
pause
