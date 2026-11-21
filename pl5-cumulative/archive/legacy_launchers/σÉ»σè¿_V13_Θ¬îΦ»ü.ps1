$ErrorActionPreference = 'Stop'
Set-Location 'D:\pl5\research_backend_v13'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw '请安装uv并使用Python3.12' }
& uv sync --python 3.12 --extra agent --extra fulltext --group dev
if ($LASTEXITCODE -ne 0) { throw '后端依赖安装失败' }
& uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw '后端测试失败' }
Set-Location 'D:\pl5\frontend'
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) { throw '请安装Node24 + pnpm11.25.0' }
& pnpm install --frozen-lockfile
if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败' }
& pnpm test
if ($LASTEXITCODE -ne 0) { throw '前端测试失败' }
& pnpm typecheck
if ($LASTEXITCODE -ne 0) { throw '前端类型检查失败' }
& pnpm build
if ($LASTEXITCODE -ne 0) { throw '前端构建失败' }
Write-Host 'V1.3 后端和原生五序前端测试全部通过；可分别启动服务。'
