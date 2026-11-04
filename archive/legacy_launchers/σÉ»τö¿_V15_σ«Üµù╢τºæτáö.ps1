param([string]$Root='D:\pl5',[int]$Hours=6)
$ErrorActionPreference='Stop'
if($Hours -lt 1 -or $Hours -gt 24){throw 'Hours必须为1-24'}
$script=Join-Path $Root 'research_backend_v15\定时科研_V15_运行.ps1'
if(-not(Test-Path $script)){throw 'V1.5尚未安装'}
foreach($old in @('PL5_AutoResearch_V05','PL5_AutoResearch_V10','PL5_AutoResearch_V15')){
 if(Get-ScheduledTask -TaskName $old -ErrorAction SilentlyContinue){throw "任务$old已存在，先由用户手动检查/停用，避免重复运行"}
}
$exe="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$arg='-NoProfile -ExecutionPolicy Bypass -File "'+$script+'" -Root "'+$Root+'"'
$action=New-ScheduledTaskAction -Execute $exe -Argument $arg -WorkingDirectory (Join-Path $Root 'research_backend_v15')
$trigger=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Hours $Hours) -RepetitionDuration (New-TimeSpan -Days 1)
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 45) -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName 'PL5_AutoResearch_V15' -Action $action -Trigger $trigger -Settings $settings -Description 'PL5 research-only metadata and health monitoring; no auto promotion or paid calls' | Out-Null
Write-Host 'V1.5科研任务已登记（需Windows本机正常运行）。默认不会自动暂停算法，除非人工执行带AutoPause的巡检命令。'
