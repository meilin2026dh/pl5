$ErrorActionPreference='Stop'
$name='PL5_AutoResearch_V17'
if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){
 Disable-ScheduledTask -TaskName $name | Out-Null
 Write-Host "已禁用 $name（未删除历史研究数据）。"
}else{Write-Host '未发现V1.7定时科研任务。'}
