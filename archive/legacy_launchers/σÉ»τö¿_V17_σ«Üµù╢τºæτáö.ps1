param([string]$Root='D:\pl5',[int]$Hours=6)
$ErrorActionPreference='Stop'
if((24 % $Hours) -ne 0 -or $Hours -lt 1 -or $Hours -gt 24){throw 'Hours需是24的因数（1,2,3,4,6,8,12,24）'}
$Backend=Join-Path $Root 'research_backend_v17'
$Script=Join-Path $Backend '科研任务_V17_执行.ps1'
# Main install copies the backend only; ship a self-contained scheduled runner inside it.
if(-not(Test-Path $Script)) {throw "定时运行脚本不存在：$Script"}
foreach($Old in @('PL5_AutoResearch_V05','PL5_AutoResearch_V10','PL5_AutoResearch_V15','PL5_AutoResearch_V17')){
 if(Get-ScheduledTask -TaskName $Old -ErrorAction SilentlyContinue){throw "任务 $Old 已存在。请先检查、停用旧任务，避免重复或覆盖。"}
}
$exe="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$arguments='-NoProfile -ExecutionPolicy Bypass -File "'+$Script+'" -Root "'+$Root+'"'
$action=New-ScheduledTaskAction -Execute $exe -Argument $arguments -WorkingDirectory $Backend
# Independent *daily* triggers: no one-day repetition expiration and no duplicate task registrations.
$base=(Get-Date).Date
$triggers=@()
for($i=0;$i -lt 24;$i+=$Hours){$triggers+=New-ScheduledTaskTrigger -Daily -At $base.AddHours($i).AddMinutes(10)}
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 50) -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName 'PL5_AutoResearch_V17' -Action $action -Trigger $triggers -Settings $settings -Description 'PL5 metadata + official archive + development-only tests; no automatic algorithm approval or paid LLM' | Out-Null
Write-Host '长期科研计划任务已注册。需要Windows开机并具备网络，系统休眠可能导致错过运行。'
