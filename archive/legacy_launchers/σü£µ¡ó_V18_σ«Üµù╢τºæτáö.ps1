$ErrorActionPreference='Stop'
$task=Get-ScheduledTask -TaskName 'PL5_AutoResearch_V18' -ErrorAction SilentlyContinue
if($task){Disable-ScheduledTask -TaskName 'PL5_AutoResearch_V18'|Out-Null;Write-Host 'V1.8科研任务已禁用，历史数据保留'}
else {Write-Host 'V1.8任务不存在'}
