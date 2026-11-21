param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v25'
if (-not (Test-Path $Backend)) { throw 'V2.5未安装' }
Set-Location $Backend
$Db=Join-Path $Root 'runtime\representation_v25.sqlite'
$Report=Join-Path $Root 'reports\representation_v25_last_cycle.json'
& uv run --no-sync python research_v25.py cycle --db $Db --count 24 --report $Report
if ($LASTEXITCODE -ne 0) { throw 'V2.5研究循环失败' }
