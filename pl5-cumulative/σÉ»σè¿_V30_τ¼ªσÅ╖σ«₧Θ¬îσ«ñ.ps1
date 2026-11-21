param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v30'
if(-not(Test-Path $Backend)){throw '请先安装V3.0'}
Set-Location $Backend
& uv run streamlit run 'pages/18_符号回归与算子压缩实验室.py'
