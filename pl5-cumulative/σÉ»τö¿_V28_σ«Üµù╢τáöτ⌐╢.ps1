param([string]$Root='D:\pl5',[string]$HistoryCsv='D:\pl5\data\official_history.csv')
$ErrorActionPreference='Stop'
if(-not(Test-Path $HistoryCsv)){throw '请先准备并核验官方开奖CSV'}
$Backend=Join-Path $Root 'research_backend_v28'
if(-not(Test-Path $Backend)){throw '请先安装V2.8'}
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '找不到uv'}
$uv=(Get-Command uv).Source
$scriptPath=Join-Path $Root 'runtime\PL5_V28_科研任务.ps1'
New-Item -ItemType Directory -Force (Join-Path $Root 'runtime')|Out-Null
$body="Set-Location '$Backend'`r`n& '$uv' run python research_v28.py study --history '$HistoryCsv' --maximum 12 --budget 100 --report '$Root\reports\v28_latest_report.json' --registry '$Root\runtime\v28_research.sqlite'`r`n"
[IO.File]::WriteAllText($scriptPath,$body,[Text.UTF8Encoding]::new($false))
$old=Get-ScheduledTask -TaskName 'PL5_V28_AutoLift' -ErrorAction SilentlyContinue
if($old){throw '存在同名任务，拒绝静默覆盖；请手动管理旧任务'}
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger=New-ScheduledTaskTrigger -Daily -At '08:00'
$trigger.Repetition.Interval='PT6H';$trigger.Repetition.Duration='P1D'
Register-ScheduledTask -TaskName 'PL5_V28_AutoLift' -Action $action -Trigger $trigger -Description '受限算子研究；不自动批准或购买' | Out-Null
Write-Host '已注册Windows定时科研任务。请检查旧版任务并确保不会重复运行。'
