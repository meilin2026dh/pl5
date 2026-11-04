# PL5 AutoResearch: scheduled scanner; no automatic installation, betting or remote code execution.
param(
    [string]$ProjectRoot = 'D:\pl5',
    [string]$OfficialCsv = '',
    [string]$OfficialSource = ''
)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $ProjectRoot
$py=Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if(-not(Test-Path $py)){ throw '缺少项目.venv；先在D:\pl5执行 uv sync --python 3.12 --extra agent --group dev' }
# Load explicitly authorized local CSV/source if configured at task enrollment.
$settings=Join-Path $ProjectRoot 'runtime\research_schedule.json'
if(( -not $OfficialCsv) -and (Test-Path -LiteralPath $settings -PathType Leaf)){
    $cfg=Get-Content -LiteralPath $settings -Raw | ConvertFrom-Json
    if($cfg.official_csv -and $cfg.official_source){
        $OfficialCsv=[string]$cfg.official_csv
        $OfficialSource=[string]$cfg.official_source
    }
}
$arguments=@('research_cli.py','cycle')
if($OfficialCsv){
    if(-not $OfficialSource){ throw '使用开奖CSV必须同时设置官方公告来源' }
    $arguments+=@('--csv',$OfficialCsv,'--official-source',$OfficialSource)
}
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot 'research_reports') | Out-Null
$log=Join-Path $ProjectRoot 'research_reports\schedule_latest.log'
& $py @arguments *>&1 | Out-File -FilePath $log -Encoding utf8
if($LASTEXITCODE -ne 0){ throw "科研巡检失败，查看 $log" }

# Optional, explicit paid abstract interpretation. At most 2 new papers per run.
# Disabled by default: user must set PL5_ENABLE_PAID_LLM=1 and OPENAI_API_KEY.
if($env:PL5_ENABLE_PAID_LLM -eq '1' -and $env:OPENAI_API_KEY){
    & $py 'research_cli.py' 'analyze' '--limit' '2' *>&1 | Out-File -FilePath $log -Append -Encoding utf8
    if($LASTEXITCODE -ne 0){ throw "LLM论文分析失败，查看 $log" }
}

# V0.6 bounded, idempotent follow-up: consume newly scanned research leads,
# invent safe expression hypotheses and persist candidates without activating them.
# Only perform development audits when caller explicitly supplies an officially verified CSV.
$cycleArgs=@('research_v06.py','ingest-leads','--max-documents','3')
& $py @cycleArgs *>&1 | Out-File -FilePath $log -Append -Encoding utf8
if($LASTEXITCODE -ne 0){ throw "V0.6线索入库失败，查看 $log" }
$cycleArgs=@('research_v06.py','cycle','--max-documents','3','--algorithms-per-document','2')
if($OfficialCsv){ $cycleArgs+=@('--csv',$OfficialCsv,'--official-source',$OfficialSource) }
& $py @cycleArgs *>&1 | Out-File -FilePath $log -Append -Encoding utf8
if($LASTEXITCODE -ne 0){ throw "V0.6科研循环失败，查看 $log" }

# V0.7 novelty-gated discovery: pick up to 2 papers and propose non-redundant
# formulas only. Never seals future draws, promotes models or places bets.
$noveltyArgs=@('research_v07.py','discover-all','--max-documents','2','--per-document','2')
& $py @noveltyArgs *>&1 | Out-File -FilePath $log -Append -Encoding utf8
if($LASTEXITCODE -ne 0){ throw "V0.7非冗余指标发现失败，查看 $log" }

# V0.8: register new Python research proposals without executing any generated code.
# Scheduled LLM code generation additionally requires two explicit environment opt-ins.
$openPythonArgs=@('research_v08.py','auto-propose','--max-documents','2')
if($env:PL5_ENABLE_PAID_PYTHON_CODE -eq '1' -and $env:PL5_ENABLE_PAID_LLM -eq '1' -and $env:OPENAI_API_KEY){
    $openPythonArgs+=@('--paid-llm','--confirm-paid')
}
& $py @openPythonArgs *>&1 | Out-File -FilePath $log -Append -Encoding utf8
if($LASTEXITCODE -ne 0){ throw "V0.8 Python科研提案失败，查看 $log" }

# V0.9: only read the evidence ledger; never auto-register, auto-settle or promote models.
& $py 'research_v09.py' 'report' *>&1 | Out-File -FilePath $log -Append -Encoding utf8
if($LASTEXITCODE -ne 0){ throw "V0.9证据台账审计失败，查看 $log" }
