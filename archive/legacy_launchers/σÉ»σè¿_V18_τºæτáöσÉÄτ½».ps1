param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
Set-Location (Join-Path $Root 'research_backend_v18')
$env:PL5_REGISTRY_PATH=Join-Path $Root 'runtime\algorithm_registry_v14.sqlite'
$env:PL5_AAN_DB=Join-Path $Root 'runtime\algorithm_abilities_v18.sqlite'
$env:PL5_OFFICIAL_CACHE=Join-Path $Root 'frontend\.cache\history.json'
$env:PL5_FORWARD_DB=Join-Path $Root 'runtime\sculpt_evidence_v152.sqlite'
$env:PL5_V17_SUPERVISOR_DB=Join-Path $Root 'runtime\research_supervisor_v17.sqlite'
$env:PL5_V17_OFFICIAL_ARCHIVE=Join-Path $Root 'data\official_archive_v17'
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '请先安装uv'}
& uv run --no-sync python integration_server.py
