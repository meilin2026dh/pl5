@echo off
setlocal
cd /d "%~dp0research_backend"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.12 or newer.
  exit /b 2
)
py -3.12 research_methods_v376.py --historical ..\runs\autonomous_v375 --output ..\runs\autonomous_v376_demo --studies 4 --budget 500 --seed 37681 --control-every 4
if errorlevel 1 (
  echo V3.7.6 study paused; inspect stderr and locked artifacts. Do NOT delete evidence blindly.
  exit /b 2
)
echo Bounded study complete; review runs\autonomous_v376_demo\state.json
endlocal
