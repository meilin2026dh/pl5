$ErrorActionPreference='Stop'
$Name='PL5_V31_CategoryResearch'
if(Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue){
 Unregister-ScheduledTask -TaskName $Name -Confirm:$false
 Write-Host '已停止并移除PL5 V3.1专属科研计划任务'
}else{Write-Host '未找到V3.1研究计划任务'}
