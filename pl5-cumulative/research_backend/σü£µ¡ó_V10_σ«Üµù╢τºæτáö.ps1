$ErrorActionPreference='Stop'
$task=Get-ScheduledTask -TaskName 'PL5_AutoResearch_V10' -ErrorAction SilentlyContinue
if($task){Unregister-ScheduledTask -TaskName 'PL5_AutoResearch_V10' -Confirm:$false}
Write-Host 'PL5 V1.0定时任务已停止（如果存在）。'
