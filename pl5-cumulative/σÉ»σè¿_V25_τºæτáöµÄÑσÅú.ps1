param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v25'
if (-not (Test-Path $Backend)) { throw 'V2.5未安装' }
Set-Location $Backend
$env:PL5_REPRESENTATION_DB=Join-Path $Root 'runtime\representation_v25.sqlite'
& uv run --no-sync python integration_server.py
