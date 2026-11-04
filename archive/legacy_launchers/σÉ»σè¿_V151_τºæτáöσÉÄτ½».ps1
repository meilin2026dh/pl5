param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v151'
Set-Location $Backend
$env:PL5_REGISTRY_PATH=Join-Path $Root 'runtime\algorithm_registry_v14.sqlite'
$env:PL5_OFFICIAL_CACHE=Join-Path $Root 'frontend\.cache\history.json'
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '请先安装uv'}
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw '安装Python依赖失败'}
& uv run python integration_server.py
