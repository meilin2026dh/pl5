param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v20'
$Frontend=Join-Path $Root 'frontend'
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv'}
Set-Location $Backend
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw 'Python依赖同步失败'}
& uv run --no-sync pytest -q
if($LASTEXITCODE -ne 0){throw 'Python回归测试失败'}
& uv run --no-sync python research_v20.py --db (Join-Path $Root 'runtime\autoresearch.sqlite') status
if($LASTEXITCODE -ne 0){throw '论文方法科研状态查询失败'}
Set-Location $Frontend
if(-not(Get-Command pnpm -ErrorAction SilentlyContinue)){throw '缺少pnpm'}
& pnpm install --frozen-lockfile
if($LASTEXITCODE -ne 0){throw '前端依赖同步失败'}
& pnpm test
if($LASTEXITCODE -ne 0){throw 'GitHub前端测试失败'}
& pnpm typecheck
if($LASTEXITCODE -ne 0){throw 'TypeScript类型检查失败'}
& pnpm build
if($LASTEXITCODE -ne 0){throw 'GitHub生产构建失败'}
Write-Host 'V2.0本机测试通过，仍需另行验收真实官方联机和Docker实验。'
