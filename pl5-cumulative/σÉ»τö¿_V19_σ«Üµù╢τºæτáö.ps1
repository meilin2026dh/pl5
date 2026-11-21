param([string]$Root='D:\pl5',[int]$Hours=6)
$ErrorActionPreference='Stop'
if($Hours -ne 6){throw 'V1.9需6小时轮换四个研究目标'}
$Backend=Join-Path $Root 'research_backend_v19'
$Script=Join-Path $Root '科研任务_V19_执行.ps1'
if(-not(Test-Path $Script) -or -not(Test-Path $Backend)){throw '请先完成V1.9安装'}
foreach($Old in @('PL5_AutoResearch_V05','PL5_AutoResearch_V10','PL5_AutoResearch_V15',
   'PL5_AutoResearch_V17','PL5_AutoResearch_V18','PL5_AutoResearch_V19')){
 if(Get-ScheduledTask -TaskName $Old -ErrorAction SilentlyContinue){throw "检测到任务 $Old，请先核实并停止，避免并发科研"}
}
$exe="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$argsLine='-NoProfile -ExecutionPolicy Bypass -File "'+$Script+'" -Root "'+$Root+'"'
$action=New-ScheduledTaskAction -Execute $exe -Argument $argsLine -WorkingDirectory $Backend
$base=(Get-Date).Date
$triggers=@()
for($hour=0;$hour -lt 24;$hour+=6){$triggers+=New-ScheduledTaskTrigger -Daily -At $base.AddHours($hour).AddMinutes(10)}
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 50) -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName 'PL5_AutoResearch_V19' -Action $action -Trigger $triggers -Settings $settings -Description 'PL5 autonomous research & bounded algorithm ability creation; research only'|Out-Null
Write-Host 'V1.9科研任务已注册，默认每6小时运行。没有自动投注或批准算法。'
