# Explicit opt-in. Task runs when this Windows user is logged in, every six hours.
param([string]$ProjectRoot='D:\pl5', [int]$Hours=6,
      [string]$OfficialCsv='', [string]$OfficialSource='')
$ErrorActionPreference='Stop'
if($Hours -lt 1 -or $Hours -gt 24){throw 'Hours需要1..24'}
# Optional, explicit consent to analyze an operator-verified official CSV each cycle.
# Data and declaration stay on the local machine, not inside scheduled command arguments.
if($OfficialCsv){
    if(-not(Test-Path -LiteralPath $OfficialCsv -PathType Leaf)){throw "CSV文件不存在：$OfficialCsv"}
    if(-not($OfficialSource.StartsWith('official:') -or $OfficialSource.StartsWith('https://'))){
        throw '需要明确官方数据来源核验声明'
    }
    $state=Join-Path $ProjectRoot 'runtime'
    New-Item -ItemType Directory -Force -Path $state | Out-Null
    $settings=@{official_csv=$OfficialCsv;official_source=$OfficialSource} | ConvertTo-Json
    $settings | Set-Content -LiteralPath (Join-Path $state 'research_schedule.json') -Encoding UTF8
}
$script=Join-Path $ProjectRoot '定时科研_运行.ps1'
if(-not(Test-Path -LiteralPath $script)){throw "文件不存在 $script"}
$ps="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$arguments='-NoProfile -ExecutionPolicy Bypass -File "'+$script+'" -ProjectRoot "'+$ProjectRoot+'"'
$action=New-ScheduledTaskAction -Execute $ps -Argument $arguments -WorkingDirectory $ProjectRoot
$start=(Get-Date).AddMinutes(3)
# One-day repeating interval, recreated each day by Task Scheduler.
$trigger=New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval (New-TimeSpan -Hours $Hours) -RepetitionDuration (New-TimeSpan -Days 1)
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 50) -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'PL5_AutoResearch_V05' -Action $action -Trigger $trigger -Settings $settings -Description '周期监测论文与开源项目，不运行外部代码、不自动修改正式算法库' -Force | Out-Null
Write-Host '已登记任务：PL5_AutoResearch_V05；请在任务计划程序中查看运行历史。'
