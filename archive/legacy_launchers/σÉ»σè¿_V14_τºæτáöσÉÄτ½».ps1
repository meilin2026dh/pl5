$ErrorActionPreference='Stop'
Set-Location 'D:\pl5\research_backend_v14'
if(-not (Get-Command uv -ErrorAction SilentlyContinue)){throw '请先安装uv'}
$env:PL5_REGISTRY_PATH='D:\pl5\runtime\algorithm_registry_v14.sqlite'
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw 'uv依赖同步失败'}
& uv run python integration_server.py
