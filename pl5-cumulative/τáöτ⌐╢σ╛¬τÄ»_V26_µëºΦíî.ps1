param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v26'
if (-not (Test-Path $Backend)) { throw 'V2.6未安装' }
Set-Location $Backend
$Db=Join-Path $Root 'runtime\hdse_v26.sqlite'
$Dir=Join-Path $Root 'reports'
New-Item -ItemType Directory -Path $Dir -Force | Out-Null
$Stamp=Get-Date -Format 'yyyyMMdd_HHmmss'
$Report=Join-Path $Dir "hdse_v26_cycle_$Stamp.json"
& uv run --no-sync python research_v26.py cycle --db $Db --maximum 12 --report $Report
if ($LASTEXITCODE -ne 0) { throw 'V2.6能力增长循环失败' }
