@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v31.ps1"
if errorlevel 1 (
 echo V3.1 installation failed. Check PowerShell output.
 exit /b 1
)
