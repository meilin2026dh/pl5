param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v31'
if(-not(Test-Path $Backend)){throw '请先安装V3.1'}
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv，请先安装Python3.12与uv'}
Set-Location $Backend
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw '依赖安装失败'}
& uv run python -m pytest -q tests/test_primitive_categories_v31.py tests/test_symbolic_v30.py tests/test_primitive_v29.py
if($LASTEXITCODE -ne 0){throw 'V3.1关键测试失败'}
& uv run python research_v31.py demo --report (Join-Path $Root 'reports\V31_windows_demo.json') --registry (Join-Path $Root 'runtime\v31_categories.sqlite')
if($LASTEXITCODE -ne 0){throw 'V3.1演示失败'}
Write-Host 'V3.1 Windows核心验证通过。科研代码仍需在真实官方数据和未来开奖做前向验证。'
