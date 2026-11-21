$ErrorActionPreference='Stop'
foreach($time in @('0020','0620','1220','1820')){
 $name='PL5_V33_MathResearch_'+$time
 if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){
  Unregister-ScheduledTask -TaskName $name -Confirm:$false
  Write-Host "已停止：$name"
 }
}
