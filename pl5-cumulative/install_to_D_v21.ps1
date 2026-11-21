param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Source=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if(-not(Test-Path $Drive)){throw "目标磁盘不存在：$Drive"}
$Backend=Join-Path $Root 'research_backend_v21'
$Frontend=Join-Path $Root 'frontend'
if(Test-Path $Backend){throw "V2.1后端已存在，不覆盖：$Backend"}
if(-not(Get-Command git -ErrorAction SilentlyContinue)){throw '缺少Git'}
if(-not(Get-Command python -ErrorAction SilentlyContinue)){throw '缺少Python'}
New-Item -ItemType Directory -Force $Root|Out-Null
if(-not(Test-Path $Frontend)){
  & git clone https://github.com/meilin2026dh/pl5.git $Frontend
  if($LASTEXITCODE -ne 0){throw 'GitHub克隆失败'}
  Push-Location $Frontend
  try {
    $Pinned='9eb9ec5ad542877680755bccf27345298ef7b99f'
    & git cat-file -e "$Pinned^{commit}"
    if($LASTEXITCODE -ne 0){throw '受审查的基础GitHub提交缺失'}
    & git switch -c pl5-v21-open-science $Pinned
    if($LASTEXITCODE -ne 0){throw '切换基础版本失败'}
  }finally{Pop-Location}
}
if(-not(Test-Path (Join-Path $Frontend 'src\pages\Workbench.tsx'))){throw '前端GitHub源码不完整'}
# Fail closed when any existing overlay file was modified; previous overlays are applied transitively.
& python (Join-Path $Source 'integration_tests\upgrade_github_overlay_v21.py') --github-root $Frontend
if($LASTEXITCODE -ne 0){throw '安全前端增量安装失败。保留用户已有文件。'}
Copy-Item -Recurse (Join-Path $Source 'research_backend') $Backend
foreach($p in @('runtime','data\official_archive_v17','reports\v21')){
  New-Item -ItemType Directory -Force (Join-Path $Root $p)|Out-Null
}
foreach($name in @('科研任务_V21_执行.ps1','启用_V21_定时科研.ps1','停止_V21_定时科研.ps1','启动_V21_科研后端.ps1','启动_V21_五序前端.ps1','验证_V21.ps1')){
  $target=Join-Path $Root $name
  if(Test-Path $target){throw "发现已有启动脚本，不主动覆盖：$target"}
  Copy-Item (Join-Path $Source $name) $target
}
Write-Host "V2.1已安装在 $Backend；原数据与旧版后端未删除。未启动后台科研、模型付费调用或代码执行。"
