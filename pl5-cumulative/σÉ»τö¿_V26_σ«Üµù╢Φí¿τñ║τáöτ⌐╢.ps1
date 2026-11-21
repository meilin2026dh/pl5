param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Task='PL5_V26_HDSE_Research'
$Runner=Join-Path $Root '研究循环_V26_执行.ps1'
if (-not (Test-Path $Runner)) { throw '先安装V2.6任务脚本' }
& schtasks /Query /TN $Task *> $null
if ($LASTEXITCODE -eq 0) { throw 'V2.6任务已存在，拒绝覆盖' }
$Action='powershell.exe -NoProfile -ExecutionPolicy Bypass -File "'+$Runner+'"'
& schtasks /Create /TN $Task /TR $Action /SC DAILY /ST '00:15' /RI 360 /DU '23:59'
if ($LASTEXITCODE -ne 0) { throw '注册失败，请检查任务计划程序权限' }
Write-Host '每6小时自动生成并记录研究假设；不自动读取历史留出集、不自动发布算法或投注。请检查旧任务是否重复。'
