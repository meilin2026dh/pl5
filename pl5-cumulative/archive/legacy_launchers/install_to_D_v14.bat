@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v14.ps1"
if errorlevel 1 (
 echo V1.4 deployment failed - see the error above.
 pause
 exit /b 1
)
pause
