param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
Set-Location (Join-Path $Root 'research_backend_v15')
$env:PL5_REGISTRY_PATH=Join-Path $Root 'runtime\algorithm_registry_v14.sqlite'
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '未安装uv'}
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw '依赖安装失败'}
& uv run python integration_server.py
