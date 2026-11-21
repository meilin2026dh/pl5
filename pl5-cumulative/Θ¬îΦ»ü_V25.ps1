param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v25'
if (-not (Test-Path $Backend)) { throw '先运行install_to_D_v25.bat' }
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw '未安装uv。请先配置Python3.12与uv' }
Set-Location $Backend
& uv sync --python 3.12 --group dev
if ($LASTEXITCODE -ne 0) { throw 'uv依赖安装失败' }
& uv run python -m pytest -q tests/test_representation_v25.py tests/test_http_spaces_v25.py tests/test_http_spaces_v24.py tests/test_nine_spaces_v24.py tests/test_temporal_spaces_v24.py
if ($LASTEXITCODE -ne 0) { throw 'V2.5或V2.4兼容测试失败' }
& uv run python research_v25.py propose --count 5 --seed 20261102 --report reports/v25_install_check.json
if ($LASTEXITCODE -ne 0) { throw '空间提案执行失败' }
Write-Host '专项验证完成；此结果不是实票预测效果验证。'
