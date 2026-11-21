param([string]$Root='D:\pl5',[string]$HistoryCsv='')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v33'
if(-not(Test-Path $Backend)){throw '请先安装V3.3'}
Set-Location $Backend
$Registry=Join-Path $Root 'runtime\v33_metalearning.sqlite'
$Report=Join-Path $Root 'reports\v33_latest.json'
$Args=@('run','python','research_v33.py','demo','--registry',$Registry,'--report',$Report)
if($HistoryCsv -ne ''){
    if(-not(Test-Path $HistoryCsv)){throw '历史CSV不存在'}
    $Args=@('run','python','research_v33.py','study','--history',$HistoryCsv,'--registry',$Registry,'--report',$Report)
}
& uv @Args
if($LASTEXITCODE -ne 0){throw '研究任务失败'}
