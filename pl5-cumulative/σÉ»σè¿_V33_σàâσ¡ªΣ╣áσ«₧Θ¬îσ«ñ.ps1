param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v33'
if(-not(Test-Path (Join-Path $Backend 'pages\21_算子元学习与性质发现.py'))){throw 'V3.3安装不存在'}
Set-Location $Backend
& uv run streamlit run 'pages/21_算子元学习与性质发现.py'
