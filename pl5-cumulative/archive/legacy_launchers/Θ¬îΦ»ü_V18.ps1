param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
Set-Location (Join-Path $Root 'research_backend_v18')
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '需要uv + Python3.12'}
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw 'Python依赖安装失败'}
& uv run --no-sync pytest -q
if($LASTEXITCODE -ne 0){throw 'Python测试失败'}
$AAN=Join-Path $Root 'runtime\algorithm_abilities_v18.sqlite'
& uv run --no-sync python capability_cli_v18.py --db $AAN bootstrap
if($LASTEXITCODE -ne 0){throw 'AAN能力初始化失败'}
Set-Location (Join-Path $Root 'frontend')
if(-not(Get-Command pnpm -ErrorAction SilentlyContinue)){throw '需要Node.js 24+与pnpm 11'}
& pnpm install --frozen-lockfile
if($LASTEXITCODE -ne 0){throw '前端依赖安装失败'}
& pnpm test
if($LASTEXITCODE -ne 0){throw '五序测试失败'}
& pnpm typecheck
if($LASTEXITCODE -ne 0){throw 'TypeScript类型检查失败'}
& pnpm build
if($LASTEXITCODE -ne 0){throw '五序生产构建失败'}
Write-Host 'V1.8本机验证通过。联网API和持续运行另验收。'
