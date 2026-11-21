param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v29'
if(-not(Test-Path $Backend)){throw '请先安装V2.9'}
Set-Location $Backend
& uv run streamlit run 'pages/17_基础数学算子发明实验室.py'
