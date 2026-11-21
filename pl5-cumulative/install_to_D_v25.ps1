param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Source=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if (-not (Test-Path $Drive)) { throw "未发现目标盘符：$Drive" }
$Target=Join-Path $Root 'research_backend_v25'
if (Test-Path $Target) { throw "目标存在，拒绝覆盖：$Target" }
$Origin=Join-Path $Source 'research_backend'
$Runner=Join-Path $Root '研究循环_V25_执行.ps1'
if (Test-Path $Runner) { throw '发现已有V2.5任务脚本，安全停止' }
if (-not (Test-Path (Join-Path $Origin 'research_v25.py'))) { throw '部署包不完整' }
New-Item -ItemType Directory -Path $Root -Force | Out-Null
Copy-Item -LiteralPath $Origin -Destination $Target -Recurse
Copy-Item -LiteralPath (Join-Path $Source 'README_V25.md') -Destination (Join-Path $Target 'README_V25.md')
Copy-Item -LiteralPath (Join-Path $Source '研究循环_V25_执行.ps1') -Destination $Runner
foreach ($dir in @('data','runtime','reports')) {
    New-Item -ItemType Directory -Path (Join-Path $Root $dir) -Force | Out-Null
}
Write-Host "PL5 V2.5安装完成：$Target。未覆盖旧版本。"
