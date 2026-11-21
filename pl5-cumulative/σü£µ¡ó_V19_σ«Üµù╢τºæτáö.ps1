$ErrorActionPreference='Stop'
$task='PL5_AutoResearch_V19'
if(Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue){
 Unregister-ScheduledTask -TaskName $task -Confirm:$false
 Write-Host 'V1.9科研计划已停止并注销'
}else{Write-Host '没有已注册的V1.9科研任务'}
