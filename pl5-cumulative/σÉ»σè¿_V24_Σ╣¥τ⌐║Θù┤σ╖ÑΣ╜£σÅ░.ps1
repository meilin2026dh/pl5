param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v24'
if (-not (Test-Path $Backend)) { throw '未安装V2.4' }
Set-Location $Backend
& uv run --no-sync streamlit run phase2_app.py
