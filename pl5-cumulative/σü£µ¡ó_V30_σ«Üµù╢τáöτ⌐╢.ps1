$ErrorActionPreference='Stop'
$TaskName='PL5_V30_SymbolicResearch'
if(Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue){
 Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
 Write-Host '已停止和移除V3.0专属科研任务'
}else{Write-Host '未找到V3.0专属科研任务'}
