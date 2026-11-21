$ErrorActionPreference='Stop'
$Name='PL5_V32_HypothesisResearch'
if(Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue){
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false
    Write-Host '已移除V3.2科研任务'
} else {Write-Host '未注册V3.2科研任务'}
