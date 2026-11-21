param([string]$Root='D:\pl5',[string]$HistoryCsv='')
$ErrorActionPreference='Stop'
$Name='PL5_V32_HypothesisResearch'
if(Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue){throw '同名任务已存在，不覆盖'}
$Script=Join-Path $Root 'research_backend_v32\研究循环_V32_执行.ps1'
if(-not(Test-Path $Script)){throw '请先安装V3.2'}
Write-Warning '必须先手动停用旧版V3.1及更早科研任务，防止并行重复研究。此脚本不会自动停用或覆盖旧任务。'
$Args="-NoProfile -ExecutionPolicy Bypass -File `"$Script`" -Root `"$Root`""
if($HistoryCsv){$Args+=" -HistoryCsv `"$HistoryCsv`""}
$Action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $Args
$Triggers=@(0,6,12,18)|ForEach-Object {New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours($_).AddMinutes(15))}
$Settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName $Name -Action $Action -Trigger $Triggers -Settings $Settings -Description 'PL5 V3.2 research-only bounded category hypothesis experiments' | Out-Null
Write-Host '已登记本机定时任务。需保持Windows开机、网络和依赖可用，且需人工检查首次实际执行结果。'
