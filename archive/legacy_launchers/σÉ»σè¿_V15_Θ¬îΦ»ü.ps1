param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v15'
Set-Location $Backend
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '未安装uv'}
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw 'Python依赖安装失败'}
& uv run pytest -q
if($LASTEXITCODE -ne 0){throw 'Python回归测试失败'}
& uv run python research_v15.py --db (Join-Path $Root 'runtime\algorithm_registry_v14.sqlite') verify-ledger
if($LASTEXITCODE -ne 0){throw '注册账本校验失败'}
Set-Location (Join-Path $Root 'frontend')
if(-not(Get-Command pnpm -ErrorAction SilentlyContinue)){throw '需安装Node24和pnpm11.25.0'}
& pnpm install --frozen-lockfile
if($LASTEXITCODE -ne 0){throw '前端依赖安装失败'}
& pnpm test
if($LASTEXITCODE -ne 0){throw '前端测试失败'}
& pnpm typecheck
if($LASTEXITCODE -ne 0){throw 'TypeScript类型检查失败'}
& pnpm build
if($LASTEXITCODE -ne 0){throw '前端生产构建失败'}
Write-Host 'V1.5 Windows验证成功。'
