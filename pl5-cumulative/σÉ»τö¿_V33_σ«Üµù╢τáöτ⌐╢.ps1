param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Worker=Join-Path $Root 'research_backend_v33\研究循环_V33_执行.ps1'
if(-not(Test-Path $Worker)){throw '请先安装V3.3；此脚本仅显式调用时创建任务'}
$Times=@('00:20','06:20','12:20','18:20')
$Exe='powershell.exe'
$Arguments="-NoProfile -ExecutionPolicy Bypass -File `"$Worker`" -Root `"$Root`""
$Action=New-ScheduledTaskAction -Execute $Exe -Argument $Arguments
foreach($time in $Times){
  $name='PL5_V33_MathResearch_'+$time.Replace(':','')
  if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw "同名任务已存在，拒绝覆盖：$name"}
}
foreach($time in $Times){
  $name='PL5_V33_MathResearch_'+$time.Replace(':','')
  $Trigger=New-ScheduledTaskTrigger -Daily -At $time
  Register-ScheduledTask -TaskName $name -Action $Action -Trigger $Trigger -Description 'PL5 V3.3 有限算子合成数学科研（非真实预测）' -ErrorAction Stop | Out-Null
  Write-Host "已登记研究任务：$name"
}
