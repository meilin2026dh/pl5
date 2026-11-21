$Task='PL5_V26_HDSE_Research'
& schtasks /Delete /TN $Task /F
if ($LASTEXITCODE -ne 0) { throw '删除失败，可能任务不存在' }
Write-Host 'V2.6任务已取消'
