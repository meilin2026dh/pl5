@echo off
setlocal
rem Execute a bounded batch. Does not install a background task or access betting accounts.
set "ROOT=%~dp0"
pushd "%ROOT%research_backend" || exit /b 1
where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher not found. Install Python 3.12+ and required project dependencies.
    popd
    exit /b 2
)
py -3.12 research_autonomous_v374.py --output "%ROOT%runs\autonomous_v374" --cycles 3 --budget 500 --seed 37401 --control-every 4
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
