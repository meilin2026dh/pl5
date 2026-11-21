# 在项目目录里运行: powershell -ExecutionPolicy Bypass -File .\启动_Windows.ps1
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error '未找到 uv，请先按 https://docs.astral.sh/uv/getting-started/installation/ 安装。'
    exit 1
}
uv python install 3.12
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv sync --python 3.12 --extra agent
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run streamlit run phase2_app.py
