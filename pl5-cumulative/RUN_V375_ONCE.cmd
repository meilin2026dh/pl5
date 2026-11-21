@echo off
setlocal
rem Run a finite, auditable scientific-question cycle. No schedule is installed.
set "ROOT=%~dp0"
pushd "%ROOT%research_backend" || exit /b 1
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.12+ is required.
  popd
  exit /b 2
)
py -3.12 research_scientific_v375.py --output "%ROOT%runs\autonomous_v375" --cycles 3 --budget 500 --seed 37401 --control-every 4
set "EXITCODE=%ERRORLEVEL%"
popd
exit /b %EXITCODE%
