param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Here=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if(-not(Test-Path $Drive)){throw "目标磁盘不存在：$Drive"}
$Source=Join-Path $Here 'research_backend'
if(-not(Test-Path (Join-Path $Source 'research_v32.py'))){throw 'V3.2源码不完整'}
$Dest=Join-Path $Root 'research_backend_v32'
if(Test-Path $Dest){throw "已有V3.2目录，拒绝覆盖：$Dest。请另存备份后再安装。"}
New-Item -ItemType Directory -Force -Path $Root | Out-Null
Copy-Item -LiteralPath $Source -Destination $Dest -Recurse
Copy-Item -LiteralPath (Join-Path $Here '研究循环_V32_执行.ps1') -Destination (Join-Path $Dest '研究循环_V32_执行.ps1')
foreach($folder in @('data','runtime','reports')) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root $folder) | Out-Null
}
Write-Host "PL5 V3.2已复制到 $Dest；旧版、历史数据、GitHub前端未覆盖。"
Write-Host '请在Windows执行 验证_V32.ps1 验证本机依赖、测试与演示。'
