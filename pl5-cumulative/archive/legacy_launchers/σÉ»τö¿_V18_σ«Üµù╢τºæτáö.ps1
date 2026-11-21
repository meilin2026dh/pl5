param([string]$Root='D:\pl5',[int]$Hours=6)
$ErrorActionPreference='Stop'
if($Hours -lt 1 -or $Hours -gt 24 -or (24%$Hours) -ne 0){throw 'Hours需是24的因数'}
$Backend=Join-Path $Root 'research_backend_v18'
$Script=Join-Path $Root '科研任务_V18_执行.ps1'
if(-not(Test-Path $Script)){throw '未找到V1.8科研运行脚本'}
foreach($Old in @('PL5_AutoResearch_V05','PL5_AutoResearch_V10','PL5_AutoResearch_V15','PL5_AutoResearch_V17','PL5_AutoResearch_V18')){
 if(Get-ScheduledTask -TaskName $Old -ErrorAction SilentlyContinue){throw "检测到科研任务 $Old；请先检查并停用旧任务，避免双重运行"}
}
$exe="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$argsLine='-NoProfile -ExecutionPolicy Bypass -File "'+$Script+'" -Root "'+$Root+'"'
$action=New-ScheduledTaskAction -Execute $exe -Argument $argsLine -WorkingDirectory $Backend
$base=(Get-Date).Date
$triggers=@();for($hour=0;$hour -lt 24;$hour+=$Hours){$triggers+=New-ScheduledTaskTrigger -Daily -At $base.AddHours($hour).AddMinutes(10)}
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 50) -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName 'PL5_AutoResearch_V18' -Action $action -Trigger $triggers -Settings $settings -Description 'PL5 AAN: official archive, literature research and bounded algorithm proposals; no auto-approval'|Out-Null
Write-Host 'V1.8科研任务已注册（无自动审批/投注）。'
