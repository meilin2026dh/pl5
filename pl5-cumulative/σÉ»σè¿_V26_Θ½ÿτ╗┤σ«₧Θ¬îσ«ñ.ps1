param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v26'
if (-not (Test-Path $Backend)) { throw '请先安装V2.6' }
Set-Location $Backend
& uv run streamlit run 'pages/14_高维隐结构发现实验室.py'
