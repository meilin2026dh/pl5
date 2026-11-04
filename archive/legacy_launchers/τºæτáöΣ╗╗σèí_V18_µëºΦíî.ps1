param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v18'
if(-not(Test-Path (Join-Path $Backend 'capability_cli_v18.py'))){throw '未安装PL5 V1.8后端'}
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv'}
$env:PYTHONUTF8='1'
$Db=Join-Path $Root 'runtime\research_supervisor_v17.sqlite'
$Papers=Join-Path $Root 'runtime\autoresearch.sqlite'
$Archive=Join-Path $Root 'data\official_archive_v17'
$Aan=Join-Path $Root 'runtime\algorithm_abilities_v18.sqlite'
$Folder=Join-Path $Root 'reports\v18'
New-Item -ItemType Directory -Force $Folder|Out-Null
Set-Location $Backend
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
& uv run --no-sync python research_v17.py --db $Db --papers-db $Papers --archive $Archive once --live --sync-official --pages 2 --audit --recover-incomplete --aan-db $Aan --aan-grow 8 2>&1 | Out-File (Join-Path $Folder "run_$stamp.log") -Encoding utf8
if($LASTEXITCODE -ne 0){throw "本轮科研失败，请查看reports\v18日志。下一次允许恢复未完成任务"}
