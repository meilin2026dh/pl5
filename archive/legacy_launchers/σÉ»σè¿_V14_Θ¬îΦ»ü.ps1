$ErrorActionPreference='Stop'
Set-Location 'D:\pl5\research_backend_v14'
if(-not (Get-Command uv -ErrorAction SilentlyContinue)){throw '未发现uv'}
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw '依赖安装失败'}
& uv run pytest -q
if($LASTEXITCODE -ne 0){throw 'Python测试失败'}
& uv run python registry_v14_cli.py --db 'D:\pl5\runtime\algorithm_registry_v14.sqlite' verify-ledger
if($LASTEXITCODE -ne 0){throw '算法审计账本检查失败'}
Set-Location 'D:\pl5\frontend'
if(-not (Get-Command pnpm -ErrorAction SilentlyContinue)){throw '需要Node24、pnpm11.25.0'}
& pnpm install --frozen-lockfile
if($LASTEXITCODE -ne 0){throw '安装前端依赖失败'}
& pnpm test
if($LASTEXITCODE -ne 0){throw '前端测试失败'}
& pnpm typecheck
if($LASTEXITCODE -ne 0){throw '类型检查失败'}
& pnpm build
if($LASTEXITCODE -ne 0){throw '前端构建失败'}
Write-Host 'PL5 V1.4全链路测试通过。'
