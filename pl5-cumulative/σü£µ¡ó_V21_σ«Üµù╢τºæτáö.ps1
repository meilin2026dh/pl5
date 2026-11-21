$ErrorActionPreference='Stop'
if(Get-ScheduledTask -TaskName 'PL5_AutoResearch_V21' -ErrorAction SilentlyContinue){
  Unregister-ScheduledTask -TaskName 'PL5_AutoResearch_V21' -Confirm:$false
  Write-Host 'V2.1科研任务已停用。'
}else{Write-Host 'V2.1科研任务未登记。'}
