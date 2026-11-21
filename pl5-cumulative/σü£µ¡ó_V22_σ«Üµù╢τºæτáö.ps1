$ErrorActionPreference='Stop'
if(Get-ScheduledTask -TaskName 'PL5_AutoResearch_V22' -ErrorAction SilentlyContinue){
  Unregister-ScheduledTask -TaskName 'PL5_AutoResearch_V22' -Confirm:$false
  Write-Host 'V2.2科研任务已停用。'
}else{Write-Host 'V2.2科研任务未登记。'}
