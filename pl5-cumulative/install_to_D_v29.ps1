param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Here=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if(-not(Test-Path $Drive)){throw "目标磁盘不存在：$Drive"}
$Source=Join-Path $Here 'research_backend'
if(-not(Test-Path (Join-Path $Source 'research_v29.py'))){throw '部署源文件不完整'}
$Dest=Join-Path $Root 'research_backend_v29'
if(Test-Path $Dest){throw "拒绝覆盖已有程序：$Dest"}
New-Item -ItemType Directory -Force -Path $Root | Out-Null
Copy-Item -LiteralPath $Source -Destination $Dest -Recurse
foreach($name in @('data','runtime','reports')){New-Item -ItemType Directory -Force -Path (Join-Path $Root $name) | Out-Null}
Write-Host "PL5 V2.9已复制到 $Dest；未覆盖旧版本、历史数据或用户算法库。"
