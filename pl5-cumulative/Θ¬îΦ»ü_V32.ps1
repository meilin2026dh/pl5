param([string]$Root='D:\pl5',[switch]$Full)
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v32'
if(-not(Test-Path (Join-Path $Backend 'research_v32.py'))){throw '请先安装V3.2'}
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv，请先安装Python3.12与uv'}
Set-Location $Backend
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw '依赖安装失败'}
if($Full){
    & uv run python -m pytest -q
} else {
    & uv run python -m pytest -q tests/test_category_hypotheses_v32.py tests/test_primitive_categories_v31.py tests/test_symbolic_v30.py
}
if($LASTEXITCODE -ne 0){throw '自动化测试失败'}
& uv run python research_v32.py demo --report (Join-Path $Root 'reports\V32_windows_demo.json') --registry (Join-Path $Root 'runtime\v32_hypotheses.sqlite')
if($LASTEXITCODE -ne 0){throw 'V3.2演示失败'}
Write-Host 'V3.2核心验证通过。若需完整回归请添加 -Full；真实官方开奖前向验证未进行。'
