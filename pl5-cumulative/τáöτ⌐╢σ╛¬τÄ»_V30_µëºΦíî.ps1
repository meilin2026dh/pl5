param([string]$Root='D:\pl5', [string]$HistoryCsv='')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v30'
if(-not(Test-Path $Backend)){throw 'V3.0尚未安装'}
Set-Location $Backend
$Args=@('run','python','research_v30.py','demo','--maximum','8','--registry', (Join-Path $Root 'runtime\v30_symbolic.sqlite'),'--report',(Join-Path $Root 'reports\v30_latest_synthetic.json'))
if($HistoryCsv -ne '') {
 if(-not(Test-Path $HistoryCsv)){throw '指定的历史CSV不存在'}
 $Args=@('run','python','research_v30.py','study','--history',$HistoryCsv,'--maximum','8','--registry',(Join-Path $Root 'runtime\v30_symbolic.sqlite'),'--report',(Join-Path $Root 'reports\v30_latest_study.json'))
}
& uv @Args
if($LASTEXITCODE -ne 0){throw 'V3.0研究任务失败'}
