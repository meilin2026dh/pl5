param([string]$Root='D:\pl5',[switch]$AutoPause)
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v15'
Set-Location $Backend
$Py=Join-Path $Backend '.venv\Scripts\python.exe'
if(-not(Test-Path $Py)){throw '没有安装Python虚拟环境；先运行启动_V15_验证.ps1'}
$Db=Join-Path $Root 'runtime\algorithm_registry_v14.sqlite'
$ReportDir=Join-Path $Root 'reports\v15'
New-Item -ItemType Directory -Force -Path $ReportDir|Out-Null
# News/paper monitoring reuses the existing bounded, recoverable V1.0 pipeline.
& $Py 'research_v10.py' --db (Join-Path $Root 'runtime\autoresearch.sqlite') run --live --resume-latest --topics 'sequential multiple testing,randomness testing' --providers 'openalex,arxiv' --max-requests 6 --max-documents 3 *> (Join-Path $ReportDir 'research_latest.log')
if($LASTEXITCODE -ne 0){Write-Warning '论文巡检失败；检查reports\v15\research_latest.log'}
# Only an existing official API *cache* can be inspected here; no invented draw.
$Cache=Join-Path $Root 'frontend\.cache\history.json'
if(Test-Path $Cache){
  & $Py 'snapshot_v15.py' --cache $Cache --out (Join-Path $ReportDir 'official_cache_snapshot.json')
  if($LASTEXITCODE -eq 0){
    $Args2=@('research_v15.py','--db',$Db,'scan','--draws',(Join-Path $ReportDir 'official_cache_snapshot.json'), '--source-label','中国体育彩票官方API缓存（程序未独立验证真实性）','--report',(Join-Path $ReportDir 'competition_latest.json'))
    if($AutoPause){$Args2+='--auto-pause'}
    & $Py @Args2 *> (Join-Path $ReportDir 'competition_latest.log')
    if($LASTEXITCODE -ne 0){Write-Warning '规则健康扫描失败，查看competition_latest.log'}
  }else{Write-Warning '历史缓存过期或无效，跳过竞争评估'}
}else{Write-Warning '无官方接口缓存，跳过竞争评估，绝不使用演示数据'}
