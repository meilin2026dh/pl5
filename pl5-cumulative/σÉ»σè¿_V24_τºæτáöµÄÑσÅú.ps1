param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v24'
if (-not (Test-Path $Backend)) { throw '未安装V2.4' }
Set-Location $Backend
$env:PL5_REGISTRY_PATH=Join-Path $Root 'runtime\algorithm_registry_v14.sqlite'
$env:PL5_AAN_DB=Join-Path $Root 'runtime\algorithm_abilities_v19.sqlite'
$env:PL5_OFFICIAL_CACHE=Join-Path $Root 'frontend\.cache\history.json'
$env:PL5_FORWARD_DB=Join-Path $Root 'runtime\sculpt_evidence_v152.sqlite'
$env:PL5_PAPER_FACTORY_DB=Join-Path $Root 'runtime\autoresearch.sqlite'
& uv run --no-sync python integration_server.py
