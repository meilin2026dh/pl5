param([string]$Root='D:\pl5',[string]$HistoryCsv='D:\pl5\data\official_history.csv')
$ErrorActionPreference='Stop'
if(-not(Test-Path $HistoryCsv)){throw '缺少已核验的官方历史CSV'}
$Backend=Join-Path $Root 'research_backend_v29'
if(-not(Test-Path $Backend)){throw '请先安装V2.9'}
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv'}
$Uv=(Get-Command uv).Source
$Existing=Get-ScheduledTask -TaskName 'PL5_V29_Primitive_Invention' -ErrorAction SilentlyContinue
if($Existing){throw '同名任务已存在，拒绝覆盖'}
$TaskScript=Join-Path $Root 'runtime\PL5_V29_Primitive_Task.ps1'
$body="Set-Location '$Backend'`r`n& '$Uv' run python research_v29.py study --history '$HistoryCsv' --maximum 20 --budget 100 --report '$Root\reports\v29_latest.json' --registry '$Root\runtime\v29_primitives.sqlite' --aan-registry '$Root\runtime\v29_aan_research.sqlite'`r`n"
[IO.File]::WriteAllText($TaskScript,$body,[Text.UTF8Encoding]::new($false))
$Action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$TaskScript`""
$Trigger=New-ScheduledTaskTrigger -Daily -At '08:00'
$Trigger.Repetition.Interval='PT6H';$Trigger.Repetition.Duration='P1D'
Register-ScheduledTask -TaskName 'PL5_V29_Primitive_Invention' -Action $Action -Trigger $Trigger -Description 'PL5有限域基础算子科研，无自动正式准入' | Out-Null
Write-Host '已注册V2.9科研任务。请检查并停用不需要的旧版任务，避免并发写入。'
