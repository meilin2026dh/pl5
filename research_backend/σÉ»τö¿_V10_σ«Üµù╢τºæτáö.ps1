# Explicit interactive invocation required. This does not silently change old V0.5 task.
param([string]$ProjectRoot='D:\pl5', [int]$Hours=6)
$ErrorActionPreference='Stop'
if($Hours -lt 1 -or $Hours -gt 24){throw 'Hours需要1到24之间'}
if(-not(Test-Path -LiteralPath (Join-Path $ProjectRoot '科研中控_V10_运行.ps1'))){throw '项目未安装到指定目录'}
$old=Get-ScheduledTask -TaskName 'PL5_AutoResearch_V05' -ErrorAction SilentlyContinue
if($old){throw '发现旧版定时任务PL5_AutoResearch_V05；请先手动停用旧版任务再启用V1.0，避免重复扫描。'}
$script=Join-Path $ProjectRoot '科研中控_V10_运行.ps1'
$exe="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$arg='-NoProfile -ExecutionPolicy Bypass -File "'+$script+'" -ProjectRoot "'+$ProjectRoot+'"'
$action=New-ScheduledTaskAction -Execute $exe -Argument $arg -WorkingDirectory $ProjectRoot
$trigger=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Hours $Hours) -RepetitionDuration (New-TimeSpan -Days 1)
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 45) -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName 'PL5_AutoResearch_V10' -Action $action -Trigger $trigger -Settings $settings -Description 'PL5 V1.0 research-only scholarly metadata monitoring' -Force | Out-Null
Write-Host '已登记PL5_AutoResearch_V10；只有电脑登录且任务计划程序可运行时才能执行。'
