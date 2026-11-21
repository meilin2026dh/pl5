$ErrorActionPreference = 'Stop'
Set-Location 'D:\pl5\research_backend_v12'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw '请先安装uv' }
& uv sync --python 3.12 --group dev
if ($LASTEXITCODE -ne 0) { throw 'uv sync失败' }
& uv run python integration_server.py
