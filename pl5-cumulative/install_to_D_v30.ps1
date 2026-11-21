param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Here=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if(-not(Test-Path $Drive)){throw "目标盘不存在：$Drive"}
$Source=Join-Path $Here 'research_backend'
if(-not(Test-Path (Join-Path $Source 'research_v30.py'))){throw 'V3.0源码不完整'}
$Dest=Join-Path $Root 'research_backend_v30'
if(Test-Path $Dest){throw "拒绝覆盖旧目录：$Dest；请先人工检查或使用不同目标位置"}
New-Item -ItemType Directory -Force -Path $Root | Out-Null
Copy-Item -LiteralPath $Source -Destination $Dest -Recurse
Copy-Item -LiteralPath (Join-Path $Here '研究循环_V30_执行.ps1') -Destination (Join-Path $Dest '研究循环_V30_执行.ps1')
foreach($folder in @('data','runtime','reports')) {New-Item -ItemType Directory -Force -Path (Join-Path $Root $folder) | Out-Null}
Write-Host "V3.0完整源码安装到 $Dest；旧版V2.9未被覆盖。"
