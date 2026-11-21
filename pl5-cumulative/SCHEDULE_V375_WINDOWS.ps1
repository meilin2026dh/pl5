# Explicit opt-in only. Preview is default; never silently installs a task.
param([switch]$Install, [switch]$Remove)
$ErrorActionPreference = 'Stop'
$name = 'PL5_V375_ScientificResearch'
$runner = Join-Path $PSScriptRoot 'RUN_V375_ONCE.cmd'
if ($Install -and $Remove) { throw 'Choose -Install or -Remove, not both.' }
if ($Remove) {
  Unregister-ScheduledTask -TaskName $name -Confirm:$false
  Write-Output "Removed $name"
  exit
}
if (-not $Install) {
  Write-Output "Preview: $name will run each day at 02:00 local time (bounded, 30 min limit)."
  Write-Output "Script: $runner"
  Write-Output 'To enable, run: .\SCHEDULE_V375_WINDOWS.ps1 -Install'
  exit
}
if (-not (Test-Path -LiteralPath $runner)) { throw "Script missing: $runner" }
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
  throw "Task $name already exists; review before replacing."
}
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c "' + $runner + '"') -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Daily -At '02:00'
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -StartWhenAvailable
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Description 'Bounded offline mathematical research; no production filtering' | Out-Null
Write-Output "Registered $name, daily 02:00 local time."
