param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v34'
if(-not(Test-Path (Join-Path $Backend 'pages\22_统一参数注册与迁移研究.py'))){throw '请先安装V3.4'}
Set-Location $Backend
& uv run streamlit run 'pages/22_统一参数注册与迁移研究.py'
