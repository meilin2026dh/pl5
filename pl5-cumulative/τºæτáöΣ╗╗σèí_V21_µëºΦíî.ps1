param([string]$Root='D:\pl5',[int]$Limit=3)
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v21'
if(-not(Test-Path $Backend)){throw 'V2.1后端尚未安装'}
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv'}
if($Limit -lt 1 -or $Limit -gt 12){throw '每轮提案数量应为1至12'}
$Reports=Join-Path $Root 'reports\v21'
New-Item -ItemType Directory -Force $Reports|Out-Null
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$slot=[int][math]::Floor((Get-Date).Hour / 6)
$goals=@('cross_position','modular_structure','sequential_geometry','hybrid_features')
$goal=$goals[$slot]
$cycle=(Get-Date -Format 'yyyyMMdd')+'-'+$slot
$AAN=Join-Path $Root 'runtime\algorithm_abilities_v19.sqlite'
$Sup=Join-Path $Root 'runtime\research_supervisor_v17.sqlite'
$Papers=Join-Path $Root 'runtime\autoresearch.sqlite'
$Archive=Join-Path $Root 'data\official_archive_v17'
Set-Location $Backend
# The old research step preserves official data synchronization and hypothesis creation.
$failed=$false
& uv run --no-sync python research_v19.py --lab-db $AAN --goal $goal --limit $Limit --cycle-key $cycle --verified-archive --db $Sup --papers-db $Papers --archive $Archive once --live --sync-official --pages 2 --audit --recover-incomplete --aan-db $AAN --aan-grow 4 2>&1 | Out-File (Join-Path $Reports "legacy_$stamp.log") -Encoding utf8
if($LASTEXITCODE -ne 0){$failed=$true}
# V2.1 automatically grounds paper-method leads, without buying LLM calls or executing code.
& uv run --no-sync python research_v20.py --db $Papers auto-extract --limit $Limit 2>&1 | Out-File (Join-Path $Reports "paper_$stamp.log") -Encoding utf8
if($LASTEXITCODE -ne 0){throw 'V2.1论文方法提取失败，详见日志'}
if($failed){Write-Warning '旧科研流程部分失败，已完成方法摘录；继续科研委员会的独立规划'}

# V2.1: form bounded, resumable cooperative research plans from grounded method cards.
# No paid model calls, untrusted code execution, automatic ESSE activation, or ticket purchases.
& uv run --no-sync python research_v21.py --db $Papers auto-plan --limit $Limit 2>&1 | Out-File (Join-Path $Reports "council_$stamp.log") -Encoding utf8
if($LASTEXITCODE -ne 0){throw 'V2.1科研委员会任务规划失败，请查看日志'}
