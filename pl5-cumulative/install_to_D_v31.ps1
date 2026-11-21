param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Here=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if(-not(Test-Path $Drive)){throw "目标磁盘不存在：$Drive"}
$Source=Join-Path $Here 'research_backend'
if(-not(Test-Path (Join-Path $Source 'research_v31.py'))){throw 'V3.1完整源代码缺失'}
$Dest=Join-Path $Root 'research_backend_v31'
if(Test-Path $Dest){throw "已有目录，拒绝覆盖：$Dest"}
New-Item -ItemType Directory -Force -Path $Root | Out-Null
Copy-Item -LiteralPath $Source -Destination $Dest -Recurse
Copy-Item -LiteralPath (Join-Path $Here '研究循环_V31_执行.ps1') -Destination (Join-Path $Dest '研究循环_V31_执行.ps1')
foreach($folder in @('data','runtime','reports')) {New-Item -ItemType Directory -Force -Path (Join-Path $Root $folder) | Out-Null}
Write-Host "PL5 V3.1安装到 $Dest。旧源码、已有研究记录与GitHub前端均未覆盖。"
