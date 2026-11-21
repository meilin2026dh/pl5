param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v31'
if(-not(Test-Path $Backend)){throw '请先安装V3.1'}
Set-Location $Backend
& uv run streamlit run 'pages/19_数学算子类别自发现.py'
