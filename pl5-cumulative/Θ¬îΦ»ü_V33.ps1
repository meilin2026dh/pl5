param([string]$Root='D:\pl5',[switch]$Full)
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v33'
if(-not(Test-Path (Join-Path $Backend 'research_v33.py'))){throw '请先运行install_to_D_v33.bat'}
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv，请先安装Python3.12与uv'}
Set-Location $Backend
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw '依赖安装失败'}
if($Full){ & uv run python -m pytest -q }
else { & uv run python -m pytest -q tests/test_operator_metalearning_v33.py tests/test_meta_http_v33.py tests/test_category_hypotheses_v32.py tests/test_primitive_categories_v31.py }
if($LASTEXITCODE -ne 0){throw 'V3.3自动测试失败'}
& uv run python research_v33.py demo --registry (Join-Path $Root 'runtime\v33_meta.sqlite') --report (Join-Path $Root 'reports\v33_demo.json')
if($LASTEXITCODE -ne 0){throw 'V3.3演示运行失败'}
Write-Host 'V3.3本机数学元学习验证通过；不代表开奖预测效果已验证。' -ForegroundColor Green
