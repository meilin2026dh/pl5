param([string]$Root='D:\pl5',[string]$HistoryCsv='')
$ErrorActionPreference='Stop'
$Name='PL5_V31_CategoryResearch'
if(Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue){throw '同名任务已存在，拒绝覆盖'}
Write-Host '请先在任务计划程序中手动停用旧版PL5科研任务，避免重复研究。'
$Script=Join-Path $Root 'research_backend_v31\研究循环_V31_执行.ps1'
if(-not(Test-Path $Script)){throw '研究循环不存在，请先安装V3.1'}
$Arguments="-NoProfile -ExecutionPolicy Bypass -File `"$Script`" -Root `"$Root`""
if($HistoryCsv){$Arguments+=" -HistoryCsv `"$HistoryCsv`""}
$Action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $Arguments
$Triggers=@(0,6,12,18)|ForEach-Object {New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours($_).AddMinutes(10))}
$Settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName $Name -Action $Action -Trigger $Triggers -Settings $Settings -Description 'PL5 V3.1 bounded research-only operator category discovery' | Out-Null
Write-Host '每6小时科研任务已登记。请在Windows任务计划程序检查执行和日志。'
