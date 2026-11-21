param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Here=Split-Path -Parent $MyInvocation.MyCommand.Path
$Source=Join-Path $Here 'research_backend'
if(-not(Test-Path (Join-Path $Source 'research_v34.py'))){throw 'V3.4程序文件不完整'}
$Drive=[System.IO.Path]::GetPathRoot($Root)
if(-not(Test-Path $Drive)){throw "磁盘不存在：$Drive"}
$Dest=Join-Path $Root 'research_backend_v34'
if(Test-Path $Dest){throw "目标已存在，拒绝覆盖：$Dest"}
New-Item -ItemType Directory -Force -Path $Root | Out-Null
Copy-Item -LiteralPath $Source -Destination $Dest -Recurse -ErrorAction Stop
Write-Host "V3.4研究后端安装完成：$Dest" -ForegroundColor Green
Write-Host '旧版本及数据没有被覆盖；请继续运行 验证_V34.ps1。'
