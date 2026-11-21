param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Source=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if (-not (Test-Path $Drive)) { throw "目标磁盘不存在：$Drive" }
$Backend=Join-Path $Root 'research_backend_v24'
if (Test-Path $Backend) { throw "V2.4目录已存在，安全停止，不覆盖：$Backend" }
$SourceBackend=Join-Path $Source 'research_backend'
if (-not (Test-Path (Join-Path $SourceBackend 'research_v24.py'))) { throw '部署包不完整：缺少V2.4引擎' }
New-Item -ItemType Directory -Path $Root -Force | Out-Null
Copy-Item -LiteralPath $SourceBackend -Destination $Backend -Recurse
New-Item -ItemType Directory -Path (Join-Path $Backend 'examples') -Force | Out-Null
Copy-Item -Path (Join-Path $Source 'examples\v24*.json') -Destination (Join-Path $Backend 'examples')
Copy-Item -LiteralPath (Join-Path $Source 'README_V24.md') -Destination (Join-Path $Backend 'README_V24.md')
New-Item -ItemType Directory -Path (Join-Path $Root 'data') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Root 'runtime') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Root 'reports') -Force | Out-Null
Write-Host "PL5 V2.4安装完成：$Backend。旧程序和数据未覆盖。"
Write-Host '请运行验证_V24.ps1，之后使用启动_V24_九空间工作台.ps1'
