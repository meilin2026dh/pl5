param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v29'
if(-not(Test-Path $Backend)){throw '请先安装V2.9'}
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv；需要Python3.12'}
Set-Location $Backend
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw '依赖安装失败'}
& uv run python -m pytest -q tests/test_primitive_v29.py tests/test_autolift_v28.py tests/test_bcse_v27.py
if($LASTEXITCODE -ne 0){throw '新旧算法测试未通过'}
& uv run python research_v29.py demo --maximum 8 --budget 20 --report 'reports\V29_windows_demo.json'
if($LASTEXITCODE -ne 0){throw '演示研究无法完成'}
Write-Host 'V2.9本机基础测试通过。真实Docker、GitHub React前端和官方数据接口另行验收。'
