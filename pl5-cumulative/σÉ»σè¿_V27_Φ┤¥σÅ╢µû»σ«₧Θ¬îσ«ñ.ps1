param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v27'
if (-not (Test-Path $Backend)) { throw '请先安装V2.7' }
Set-Location $Backend
& uv run streamlit run 'pages/15_贝叶斯软约束科研实验室.py'
