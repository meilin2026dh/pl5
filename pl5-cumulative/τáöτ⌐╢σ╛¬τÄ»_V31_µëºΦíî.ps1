param([string]$Root='D:\pl5',[string]$HistoryCsv='')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v31'
if(-not(Test-Path $Backend)){throw '请先安装V3.1'}
Set-Location $Backend
$Registry=Join-Path $Root 'runtime\v31_categories.sqlite'
$Report=Join-Path $Root 'reports\V31_latest_demo.json'
$Args=@('run','python','research_v31.py','demo','--registry',$Registry,'--report',$Report)
if($HistoryCsv -ne ''){
 if(-not(Test-Path $HistoryCsv)){throw '没有找到指定CSV历史数据'}
 $Report=Join-Path $Root 'reports\V31_latest_study.json'
 $Args=@('run','python','research_v31.py','study','--history',$HistoryCsv,'--maximum','8','--registry',$Registry,'--report',$Report)
}
& uv @Args
if($LASTEXITCODE -ne 0){throw 'V3.1自主算子类别巡检失败'}
