@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v152.ps1"
if errorlevel 1 (
 echo 安装失败。原有数据未由本脚本删除，请查看上面的报错。
 pause
 exit /b 1
)
echo 源码接入完成，请继续验证。
pause
