param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v17'
Set-Location $Backend
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '请安装uv'}
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw '安装Python依赖失败'}
& uv run --no-sync pytest -q tests/test_autonomous_v17.py
if($LASTEXITCODE -ne 0){throw 'V1.7新增科研测试未通过'}
& uv run --no-sync python research_v17.py --db (Join-Path $Root 'runtime\research_supervisor_v17.sqlite') --archive (Join-Path $Root 'data\official_archive_v17') status
if($LASTEXITCODE -ne 0){throw 'V1.7状态读取失败'}
Set-Location (Join-Path $Root 'frontend')
if(-not(Get-Command pnpm -ErrorAction SilentlyContinue)){throw '请安装Node24和pnpm11'}
& pnpm install --frozen-lockfile
if($LASTEXITCODE -ne 0){throw '前端依赖失败'}
& pnpm test
if($LASTEXITCODE -ne 0){throw '前端测试失败'}
& pnpm typecheck
if($LASTEXITCODE -ne 0){throw 'TypeScript类型检查失败'}
& pnpm build
if($LASTEXITCODE -ne 0){throw '五序生产构建失败'}
Write-Host 'V1.7测试通过（仍需实际联网、浏览器、计划任务实机验收）'
