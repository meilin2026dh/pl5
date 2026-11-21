param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v30'
if(-not(Test-Path $Backend)){throw '请先部署V3.0'}
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv；请先安装uv与Python3.12'}
Set-Location $Backend
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw '安装依赖失败'}
& uv run python -m pytest -q tests/test_symbolic_v30.py tests/test_primitive_v29.py
if($LASTEXITCODE -ne 0){throw '核心测试失败'}
& uv run python research_v30.py formula-demo --report 'reports\V30_windows_formula_demo.json'
if($LASTEXITCODE -ne 0){throw '功能验证失败'}
Write-Host 'V3.0本机核心验证通过。尚需用户自行验证官方数据源与其他跨服务组件。'
