$ErrorActionPreference = 'Stop'
Set-Location 'D:\pl5\frontend'
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) { throw '需要 Node.js 24及pnpm 11.25.0' }
& pnpm install --frozen-lockfile
if ($LASTEXITCODE -ne 0) { throw 'pnpm install失败' }
& pnpm test
if ($LASTEXITCODE -ne 0) { throw '测试不通过，拒绝启动' }
& pnpm typecheck
if ($LASTEXITCODE -ne 0) { throw 'TypeScript类型检查不通过，拒绝启动' }
& pnpm dev
