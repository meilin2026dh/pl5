param([string]$Root='D:\pl5',[int]$Port=8765)
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v34'
if(-not(Test-Path (Join-Path $Backend 'integration_server.py'))){throw '请先安装V3.4'}
$env:PL5_BRIDGE_PORT="$Port"
Set-Location $Backend
& uv run python integration_server.py
