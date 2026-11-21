$ErrorActionPreference='Stop'
$Task='PL5_V25_RepresentationResearch'
& schtasks /Delete /TN $Task /F
if ($LASTEXITCODE -ne 0) { throw '任务不存在或删除失败' }
Write-Host 'V2.5研究任务已停止并删除。'
