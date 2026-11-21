param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v19'
$Front=Join-Path $Root 'frontend'
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '需要uv'}
Set-Location $Backend
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw 'Python依赖安装失败'}
& uv run --no-sync pytest -q
if($LASTEXITCODE -ne 0){throw 'Python测试未通过'}
$AAN=Join-Path $Root 'runtime\algorithm_abilities_v19.sqlite'
& uv run --no-sync python capability_cli_v18.py --db $AAN bootstrap
if($LASTEXITCODE -ne 0){throw '初始化算法注册失败'}
& uv run --no-sync python ability_cli_v19.py --db $AAN plan --goal cross_position
if($LASTEXITCODE -ne 0){throw '研究规划失败'}
Set-Location $Front
if(-not(Get-Command pnpm -ErrorAction SilentlyContinue)){throw '需要Node.js 24和pnpm 11'}
& pnpm install --frozen-lockfile
if($LASTEXITCODE -ne 0){throw '前端依赖安装失败'}
& pnpm test
if($LASTEXITCODE -ne 0){throw '前端测试失败'}
& pnpm typecheck
if($LASTEXITCODE -ne 0){throw 'TypeScript检查失败'}
& pnpm build
if($LASTEXITCODE -ne 0){throw '生产构建失败'}
Write-Host 'V1.9本机测试通过。请另外确认官方接口和定时任务实际运行。'
