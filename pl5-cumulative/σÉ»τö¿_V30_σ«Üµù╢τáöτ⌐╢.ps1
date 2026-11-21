param([string]$Root='D:\pl5', [string]$HistoryCsv='')
$ErrorActionPreference='Stop'
$TaskName='PL5_V30_SymbolicResearch'
if(Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue){throw '已存在同名任务，拒绝覆盖'}
Write-Host '启用前请手动检查并停用旧版PL5科研任务，防止重复运行。'
$Script=Join-Path $Root 'research_backend_v30\研究循环_V30_执行.ps1'
if(-not(Test-Path $Script)){throw "没有找到研究循环脚本：$Script。请重新安装V3.0，并确认研究循环脚本存在。"}
$ArgString="-NoProfile -ExecutionPolicy Bypass -File `"$Script`" -Root `"$Root`""
if($HistoryCsv){$ArgString += " -HistoryCsv `"$HistoryCsv`""}
$Action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $ArgString
$Triggers=@(0,6,12,18) | ForEach-Object { New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours($_).AddMinutes(10)) }
$Settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Triggers -Settings $Settings -Description 'PL5 V3.0 research-only symbolic compression scan' | Out-Null
Write-Host 'V3.0研究任务已注册；每6小时执行一次。请检查任务计划程序的状态和日志。'
