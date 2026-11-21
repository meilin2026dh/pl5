param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v25'
if (-not (Test-Path $Backend)) { throw 'V2.5未安装' }
Set-Location $Backend
& uv run streamlit run 'pages/13_自主表示空间发现实验室.py'
