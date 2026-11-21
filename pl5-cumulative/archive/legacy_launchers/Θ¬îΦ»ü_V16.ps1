param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
Set-Location (Join-Path $Root 'research_backend_v16')
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv'}
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw '依赖安装失败'}
& uv run pytest -q
if($LASTEXITCODE -ne 0){throw 'Python回归失败'}
Set-Location (Join-Path $Root 'frontend')
if(-not(Get-Command pnpm -ErrorAction SilentlyContinue)){throw '缺少pnpm'}
& pnpm install --frozen-lockfile
if($LASTEXITCODE -ne 0){throw '前端依赖安装失败'}
& pnpm test
if($LASTEXITCODE -ne 0){throw '五序前端测试失败'}
& pnpm typecheck
if($LASTEXITCODE -ne 0){throw 'TypeScript类型检查失败'}
& pnpm build
if($LASTEXITCODE -ne 0){throw '生产构建失败'}
Write-Host '本机代码测试和构建通过。尚需启动前后端做实际UI联调。'
