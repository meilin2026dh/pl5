param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Frontend=Join-Path $Root 'frontend'
if(-not(Test-Path $Frontend)){throw '缺少GitHub五序完整源码'}
Set-Location $Frontend
if(-not(Get-Command pnpm -ErrorAction SilentlyContinue)){throw '缺少pnpm 11及Node.js 24'}
& pnpm dev
