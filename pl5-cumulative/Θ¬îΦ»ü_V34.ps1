param([string]$Root='D:\pl5',[switch]$Full)
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v34'
if(-not(Test-Path (Join-Path $Backend 'research_v34.py'))){throw '请先运行install_to_D_v34.bat'}
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '未找到uv；请安装Python3.12与uv'}
Set-Location $Backend
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw '依赖安装失败'}
if($Full){ & uv run python -m pytest -q }
else { & uv run python -m pytest -q tests/test_parameter_hub_v34.py tests/test_transfer_evolution_v34.py tests/test_parameter_http_v34.py tests/test_operator_metalearning_v33.py tests/test_meta_http_v33.py }
if($LASTEXITCODE -ne 0){throw 'V3.4自动测试失败'}
& uv run python research_v34.py demo --audit-db (Join-Path $Root 'runtime\v34_parameter_audit.sqlite') --report (Join-Path $Root 'reports\v34_demo.json')
if($LASTEXITCODE -ne 0){throw 'V3.4演示失败'}
Write-Host 'V3.4本机科研功能通过。彩票预测性能需要单独验证。' -ForegroundColor Green
