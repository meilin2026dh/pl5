param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v28'
if(-not(Test-Path $Backend)){throw '请先安装V2.8'}
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '请先安装uv及Python3.12'}
Set-Location $Backend
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw '依赖安装失败'}
& uv run python -m pytest -q tests/test_autolift_v28.py tests/test_http_autolift_v28.py tests/test_bcse_v27.py
if($LASTEXITCODE -ne 0){throw 'V2.8专项及BCSE兼容测试未通过'}
& uv run python research_v28.py demo --maximum 6 --budget 20 --report 'reports\V28_windows_demo.json'
if($LASTEXITCODE -ne 0){throw 'V2.8科研演示失败'}
Write-Host '本机专项验收完成。官方接口、长期科研定时任务仍需单独验证。'
