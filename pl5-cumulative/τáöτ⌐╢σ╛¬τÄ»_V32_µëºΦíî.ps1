param([string]$Root='D:\pl5',[string]$HistoryCsv='')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v32'
if(-not(Test-Path $Backend)){throw '请先安装V3.2'}
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv'}
Set-Location $Backend
$Registry=Join-Path $Root 'runtime\v32_hypotheses.sqlite'
$Report=Join-Path $Root 'reports\V32_latest_demo.json'
$Args=@('run','python','research_v32.py','demo','--registry',$Registry,'--report',$Report)
if($HistoryCsv -ne '') {
    if(-not(Test-Path $HistoryCsv)){throw '指定历史CSV不存在'}
    $Report=Join-Path $Root 'reports\V32_latest_history_research.json'
    $Args=@('run','python','research_v32.py','study','--history',$HistoryCsv,'--maximum','8', '--registry',$Registry,'--report',$Report)
}
& uv @Args
if($LASTEXITCODE -ne 0){throw 'V3.2科研巡检失败'}
