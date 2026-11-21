@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_to_D_v32.ps1"
if errorlevel 1 (
 echo PL5 V3.2 installation failed. Read the PowerShell error above.
 exit /b 1
)
