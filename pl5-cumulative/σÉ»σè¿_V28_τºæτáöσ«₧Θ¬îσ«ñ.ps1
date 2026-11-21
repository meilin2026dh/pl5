param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
Set-Location (Join-Path $Root 'research_backend_v28')
& uv run streamlit run 'pages/16_自主升维与稀疏约束实验室.py'
