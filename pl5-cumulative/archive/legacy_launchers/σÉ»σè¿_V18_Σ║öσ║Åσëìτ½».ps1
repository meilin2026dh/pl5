param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
Set-Location (Join-Path $Root 'frontend')
if(-not(Get-Command pnpm -ErrorAction SilentlyContinue)){throw '需要Node24与pnpm11'}
& pnpm install --frozen-lockfile
if($LASTEXITCODE -ne 0){throw '前端依赖安装失败'}
& pnpm dev
