param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v27'
if (-not (Test-Path $Backend)) { throw '请先安装V2.7' }
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw '请先安装uv和Python 3.12' }
Set-Location $Backend
& uv sync --python 3.12 --group dev
if ($LASTEXITCODE -ne 0) { throw '依赖安装失败' }
& uv run python -m pytest -q tests/test_bcse_v27.py tests/test_http_bcse_v27.py tests/test_highdim_v26.py
if ($LASTEXITCODE -ne 0) { throw 'V2.7专项与V2.6兼容测试未通过' }
& uv run python research_v27.py demo --budget 10 --report 'examples\V27_windows_synthetic_demo.json'
if ($LASTEXITCODE -ne 0) { throw '合成样本演示失败' }
Write-Host 'V2.7专项测试通过。官方数据联机与浏览器GUI仍需人工验收。'
