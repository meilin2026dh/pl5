param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Task='PL5_V25_RepresentationResearch'
$Runner=Join-Path $Root '研究循环_V25_执行.ps1'
if (-not (Test-Path $Runner)) { throw '未安装V2.5任务脚本，请先安装' }
& schtasks /Query /TN $Task *> $null
if ($LASTEXITCODE -eq 0) { throw '已有V2.5计划任务。拒绝覆盖；请先检查现有配置' }
$Action='powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $Runner + '"'
& schtasks /Create /TN $Task /TR $Action /SC DAILY /ST '00:10' /RI 360
if ($LASTEXITCODE -ne 0) { throw '计划任务注册失败；检查权限及Windows任务计划程序' }
Write-Host '已注册V2.5每6小时研究任务。不会自动停止旧版本的计划任务。'
