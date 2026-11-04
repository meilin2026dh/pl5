$ErrorActionPreference='Stop'
Unregister-ScheduledTask -TaskName 'PL5_AutoResearch_V05' -Confirm:$false
Write-Host '已删除本机PL5定时科研任务'
