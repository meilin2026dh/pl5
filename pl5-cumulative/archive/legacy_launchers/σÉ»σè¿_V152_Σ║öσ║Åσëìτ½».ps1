param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
Set-Location (Join-Path $Root 'frontend')
if(-not(Get-Command pnpm -ErrorAction SilentlyContinue)){throw '需要Node.js 24和pnpm 11.25.0'}
& pnpm install --frozen-lockfile
if($LASTEXITCODE -ne 0){throw '安装前端依赖失败'}
& pnpm dev
