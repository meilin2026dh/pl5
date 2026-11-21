param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Source=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if(-not(Test-Path $Drive)){throw "目标磁盘不存在：$Drive"}
$Front=Join-Path $Root 'frontend'
$Backend=Join-Path $Root 'research_backend_v19'
if(Test-Path $Backend){throw "新版本已经存在，禁止覆盖：$Backend"}
New-Item -ItemType Directory -Force $Root|Out-Null
if(-not(Test-Path $Front)){
 if(-not(Get-Command git -ErrorAction SilentlyContinue)){throw '必须安装Git，才能首次克隆完整五序源码'}
 & git clone https://github.com/meilin2026dh/pl5.git $Front
 if($LASTEXITCODE -ne 0){throw 'GitHub克隆失败'}
 Push-Location $Front
 try{
  $Pinned='9eb9ec5ad542877680755bccf27345298ef7b99f'
  & git cat-file -e "$Pinned^{commit}"
  if($LASTEXITCODE -ne 0){throw '受审查的GitHub提交不存在'}
  & git switch -c pl5-v19-ability-lab $Pinned
  if($LASTEXITCODE -ne 0){throw '无法切换到受审查版本'}
 }finally{Pop-Location}
}
if(-not(Test-Path (Join-Path $Front 'src\pages\Workbench.tsx'))){throw '五序源码不完整'}
if(-not(Get-Command python -ErrorAction SilentlyContinue)){throw '需要Python3.12或兼容环境'}
# Idempotent upgrader checks and backup before updating the existing frontend.
& python (Join-Path $Source 'integration_tests\upgrade_github_overlay_v19.py') --github-root $Front
if($LASTEXITCODE -ne 0){throw '前端增量安装出现冲突，已停止'}
Copy-Item -Recurse (Join-Path $Source 'research_backend') $Backend
foreach($p in @('data\official_archive_v17','runtime','reports\v19')){
 New-Item -ItemType Directory -Force (Join-Path $Root $p)|Out-Null
}
Write-Host "V1.9已安装到 $Backend。未覆盖历史数据、未启用后台任务、未审批实验算法。"
