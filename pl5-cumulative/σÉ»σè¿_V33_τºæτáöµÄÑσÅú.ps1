param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
Set-Location (Join-Path $Root 'research_backend_v33')
& uv run python integration_server.py
