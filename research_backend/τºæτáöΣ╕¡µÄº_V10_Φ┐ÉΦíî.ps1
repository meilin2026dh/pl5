# User-initiated schedule only. No paid models, untrusted Python execution, candidate publication or betting.
param([string]$ProjectRoot='D:\pl5')
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $ProjectRoot
$python=Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $python -PathType Leaf)){throw '未找到项目Python；请先执行 uv sync'}
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot 'research_reports') | Out-Null
$log=Join-Path $ProjectRoot 'research_reports\v10_schedule_latest.log'
$arguments=@('research_v10.py','run','--live','--resume-latest','--topics','sequential multiple testing,randomness testing','--providers','openalex,arxiv','--max-requests','6','--max-documents','3')
$cfgPath=Join-Path $ProjectRoot 'runtime\v10_schedule.json'
if(Test-Path -LiteralPath $cfgPath){
    $cfg=Get-Content -LiteralPath $cfgPath -Raw | ConvertFrom-Json
    if($cfg.enable_development_audit -eq $true){
        if(-not(Test-Path -LiteralPath ([string]$cfg.official_csv) -PathType Leaf)){throw '定时科研官方数据CSV不存在'}
        $arguments+=@('--audit','--official-csv',([string]$cfg.official_csv),'--official-source',([string]$cfg.official_source))
    }
}
& $python @arguments *>&1 | Out-File -LiteralPath $log -Encoding UTF8
if($LASTEXITCODE -ne 0){throw "V1.0巡检失败，查看日志：$log"}
