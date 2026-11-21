param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v22'
$Script=Join-Path $Root '科研任务_V22_执行.ps1'
if(-not(Test-Path $Backend) -or -not(Test-Path $Script)){throw '请先完成V2.2安装'}
foreach($name in @('PL5_AutoResearch_V05','PL5_AutoResearch_V10','PL5_AutoResearch_V15',
'PL5_AutoResearch_V17','PL5_AutoResearch_V18','PL5_AutoResearch_V19','PL5_AutoResearch_V20','PL5_AutoResearch_V21','PL5_AutoResearch_V22')){
  if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw "已有科研任务 $name，需先停用，防止重复研究"}
}
$exe="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$arguments='-NoProfile -ExecutionPolicy Bypass -File "'+$Script+'" -Root "'+$Root+'"'
$action=New-ScheduledTaskAction -Execute $exe -Argument $arguments -WorkingDirectory $Backend
$base=(Get-Date).Date
$triggers=@()
for($h=0;$h -lt 24;$h+=6){$triggers+=New-ScheduledTaskTrigger -Daily -At $base.AddHours($h).AddMinutes(10)}
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 50) -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName 'PL5_AutoResearch_V22' -Action $action -Trigger $triggers -Settings $settings -Description 'PL5 bounded autonomous research + grounded paper leads, no auto-approval' | Out-Null
Write-Host '已注册V2.2定时科研（6小时一次，不自动执行外部算法）。'
