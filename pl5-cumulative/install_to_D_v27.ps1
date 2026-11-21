param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Source=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if (-not (Test-Path $Drive)) { throw "未检测到盘符：$Drive" }
$Backend=Join-Path $Source 'research_backend'
if (-not (Test-Path (Join-Path $Backend 'research_v27.py'))) { throw '部署包缺少V2.7源码' }
$Target=Join-Path $Root 'research_backend_v27'
if (Test-Path $Target) { throw "目录已存在，拒绝覆盖：$Target" }
New-Item -ItemType Directory -Force -Path $Root | Out-Null
Copy-Item -LiteralPath $Backend -Destination $Target -Recurse
Copy-Item -LiteralPath (Join-Path $Source 'README_V27.md') -Destination (Join-Path $Target 'README_V27.md')
foreach($d in @('data','runtime','reports')) { New-Item -ItemType Directory -Force -Path (Join-Path $Root $d) | Out-Null }
Write-Host "V2.7已安装至：$Target。旧版程序与用户数据不删除。"
