param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v24'
if (-not(Test-Path $Backend)) { throw '请先运行install_to_D_v24.bat' }
if (-not(Get-Command uv -ErrorAction SilentlyContinue)) { throw '需要安装uv/Python3.12' }
Set-Location $Backend
& uv sync --python 3.12 --group dev
if ($LASTEXITCODE -ne 0) { throw '依赖安装失败' }
& uv run python -m pytest -q tests/test_nine_spaces_v24.py tests/test_temporal_spaces_v24.py tests/test_http_spaces_v24.py
if ($LASTEXITCODE -ne 0) { throw 'V2.4专项测试未通过' }
& uv run python research_v24.py describe --family mod3 --metric road_key
if ($LASTEXITCODE -ne 0) { throw '指标分布命令失败' }
Write-Host 'V2.4基础环境与九空间专项测试通过。完整GitHub前端请单独验收。'
