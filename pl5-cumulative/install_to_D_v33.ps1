param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Here=Split-Path -Parent $MyInvocation.MyCommand.Path
$Source=Join-Path $Here 'research_backend'
if(-not (Test-Path (Join-Path $Source 'research_v33.py'))){throw 'V3.3源码不完整'}
$Drive=[System.IO.Path]::GetPathRoot($Root)
if(-not (Test-Path $Drive)){throw "目标磁盘不存在：$Drive"}
$Dest=Join-Path $Root 'research_backend_v33'
if(Test-Path $Dest){throw "目标目录已存在，拒绝覆盖：$Dest"}
New-Item -ItemType Directory -Force -Path $Root | Out-Null
Copy-Item -LiteralPath $Source -Destination $Dest -Recurse -ErrorAction Stop
Copy-Item -LiteralPath (Join-Path $Here '研究循环_V33_执行.ps1') -Destination (Join-Path $Dest '研究循环_V33_执行.ps1')
foreach($folder in @('data','runtime','reports')){New-Item -ItemType Directory -Force -Path (Join-Path $Root $folder) | Out-Null}
Write-Host "PL5 V3.3源码复制完成：$Dest" -ForegroundColor Green
Write-Host '未覆盖旧版本、数据、GitHub前端或任务。请运行 验证_V33.ps1。'
