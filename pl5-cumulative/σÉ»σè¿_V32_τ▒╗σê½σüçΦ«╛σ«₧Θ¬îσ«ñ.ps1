param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v32'
if(-not(Test-Path $Backend)){throw '请先安装V3.2'}
Set-Location $Backend
& uv run streamlit run 'pages/20_数学类别假设自进化.py'
