param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
Set-Location (Join-Path $Root 'research_backend_v16')
$env:PL5_REGISTRY_PATH=Join-Path $Root 'runtime\algorithm_registry_v14.sqlite'
$env:PL5_OFFICIAL_CACHE=Join-Path $Root 'frontend\.cache\history.json'
$env:PL5_FORWARD_DB=Join-Path $Root 'runtime\sculpt_evidence_v152.sqlite'
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv'}
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw 'Python依赖安装失败'}
& uv run python integration_server.py
