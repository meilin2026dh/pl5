$ErrorActionPreference='Stop'
Set-Location 'D:\pl5\frontend'
if(-not (Get-Command pnpm -ErrorAction SilentlyContinue)){throw '需要Node24和pnpm11.25.0'}
& pnpm install --frozen-lockfile
if($LASTEXITCODE -ne 0){throw '安装前端依赖失败'}
& pnpm dev
