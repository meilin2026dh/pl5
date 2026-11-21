# Explicit opt-in only. Run `powershell -File .\SCHEDULE_V374_WINDOWS.ps1 -Install`.
param([switch]$Install, [switch]$Remove)
$ErrorActionPreference = 'Stop'
$taskName = 'PL5_V374_AutonomousResearch'
$cmd = Join-Path $PSScriptRoot 'RUN_V374_ONCE.cmd'
if ($Install -and $Remove) { throw 'Choose only -Install or -Remove.' }
if ($Remove) {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
  Write-Output "Removed scheduled task $taskName"
  exit
}
if (-not $Install) {
  Write-Output "Preview only. Use -Install to schedule a daily bounded research batch at 02:00 local time."
  Write-Output "Command: $cmd"
  exit
}
if (-not (Test-Path -LiteralPath $cmd)) { throw "Missing batch file: $cmd" }
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
  throw "Task $taskName already exists. Review it before making changes."
}
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c "' + $cmd + '"') -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Daily -At '02:00'
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -StartWhenAvailable
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description 'Offline, bounded PL5 research; no betting or network calls' | Out-Null
Write-Output "Registered task $taskName (daily 02:00 local time)."
