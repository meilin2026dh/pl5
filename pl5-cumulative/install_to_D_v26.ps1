param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Source=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if (-not (Test-Path $Drive)) { throw "未检测到盘符：$Drive" }
$Origin=Join-Path $Source 'research_backend'
if (-not (Test-Path (Join-Path $Origin 'research_v26.py'))) { throw '安装包缺少V2.6源码' }
$Target=Join-Path $Root 'research_backend_v26'
if (Test-Path $Target) { throw "目标目录已存在，拒绝覆盖：$Target" }
foreach($file in @('研究循环_V26_执行.ps1')) {
    if (Test-Path (Join-Path $Root $file)) { throw "脚本已存在，拒绝覆盖：$file" }
}
New-Item -ItemType Directory -Path $Root -Force | Out-Null
Copy-Item -LiteralPath $Origin -Destination $Target -Recurse
Copy-Item -LiteralPath (Join-Path $Source 'README_V26.md') -Destination (Join-Path $Target 'README_V26.md')
Copy-Item -LiteralPath (Join-Path $Source '研究循环_V26_执行.ps1') -Destination (Join-Path $Root '研究循环_V26_执行.ps1')
foreach($dir in @('data','runtime','reports')) { New-Item -ItemType Directory -Path (Join-Path $Root $dir) -Force | Out-Null }
Write-Host "V2.6已经安装至 $Target。旧版本、原始数据和任务保持不变。" 
