param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Here=Split-Path -Parent $MyInvocation.MyCommand.Path
$Disk=Split-Path -Qualifier $Root
if(-not (Test-Path $Disk)){ throw "目标盘符不存在：$Disk" }
$Backend=Join-Path $Here 'research_backend'
if(-not (Test-Path (Join-Path $Backend 'research_v28.py'))){ throw '部署包不包含V2.8源代码' }
$Destination=Join-Path $Root 'research_backend_v28'
if(Test-Path $Destination){throw "目录已存在，拒绝覆盖：$Destination"}
New-Item -ItemType Directory -Path $Root -Force | Out-Null
Copy-Item -LiteralPath $Backend -Destination $Destination -Recurse
Copy-Item -LiteralPath (Join-Path $Here 'README_V28.md') -Destination (Join-Path $Destination 'README_V28.md')
foreach($name in @('data','runtime','reports')){New-Item -ItemType Directory -Path (Join-Path $Root $name) -Force | Out-Null}
Write-Host "V2.8已安装至：$Destination；旧代码与用户历史数据均未覆盖。"
