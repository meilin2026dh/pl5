param([string]$Root='D:\pl5',[int]$Limit=3)
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v19'
if(-not(Test-Path $Backend)){throw 'V1.9后端尚未安装'}
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv'}
if($Limit -lt 1 -or $Limit -gt 12){throw '每轮算法数量须为1—12'}
$ReportDir=Join-Path $Root 'reports\v19'
New-Item -ItemType Directory -Force $ReportDir|Out-Null
$slot=[int][math]::Floor((Get-Date).Hour / 6)
$goals=@('cross_position','modular_structure','sequential_geometry','hybrid_features')
$goal=$goals[$slot]
$cycle=(Get-Date -Format 'yyyyMMdd')+'-'+$slot
$AAN=Join-Path $Root 'runtime\algorithm_abilities_v19.sqlite'
$Sup=Join-Path $Root 'runtime\research_supervisor_v17.sqlite'
$Papers=Join-Path $Root 'runtime\autoresearch.sqlite'
$Archive=Join-Path $Root 'data\official_archive_v17'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
Set-Location $Backend
& uv run --no-sync python research_v19.py --lab-db $AAN --goal $goal --limit $Limit --cycle-key $cycle --verified-archive --db $Sup --papers-db $Papers --archive $Archive once --live --sync-official --pages 2 --audit --recover-incomplete --aan-db $AAN --aan-grow 4 2>&1 | Out-File (Join-Path $ReportDir "run_$stamp.log") -Encoding utf8
if($LASTEXITCODE -ne 0){throw '本轮V1.9科研失败，请查看日志；不会自动审批或投注'}
