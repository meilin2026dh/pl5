$ErrorActionPreference='Stop'
$task=Get-ScheduledTask -TaskName 'PL5_AutoResearch_V15' -ErrorAction SilentlyContinue
if($task){Unregister-ScheduledTask -TaskName 'PL5_AutoResearch_V15' -Confirm:$false;Write-Host 'V1.5定时科研任务已停止并注销。'}
else{Write-Host '当前没有V1.5定时科研任务。'}
