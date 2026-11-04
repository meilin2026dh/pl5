param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v17'
if(-not(Test-Path (Join-Path $Backend 'research_v17.py'))){throw '未发现V1.7后端'}
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv'}
$env:PYTHONUTF8='1'
$Db=Join-Path $Root 'runtime\research_supervisor_v17.sqlite'
$Papers=Join-Path $Root 'runtime\autoresearch.sqlite'
$Archive=Join-Path $Root 'data\official_archive_v17'
$Folder=Join-Path $Root 'reports\v17'
New-Item -ItemType Directory -Force $Folder | Out-Null
Set-Location $Backend
# Do not auto-sync dependency versions at each scheduled run.
# Initial dependencies must be installed by 验证_V17.ps1.
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
& uv run --no-sync python research_v17.py --db $Db --papers-db $Papers --archive $Archive once --live --sync-official --pages 2 --audit --recover-incomplete 2>&1 | Out-File -FilePath (Join-Path $Folder "run_$stamp.log") -Encoding utf8
$exit=$LASTEXITCODE
if($exit -ne 0){throw "科研任务执行失败，退出码$exit，请查看报告目录中的日志；下次周期可恢复未完成步骤"}
