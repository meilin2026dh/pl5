@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v30.ps1"
if errorlevel 1 (
 echo Install failed. Check PowerShell errors above.
 exit /b 1
)
