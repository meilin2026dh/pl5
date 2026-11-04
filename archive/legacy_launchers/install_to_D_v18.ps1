param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Source=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if(-not(Test-Path $Drive)){throw "目标盘不存在: $Drive"}
$Front=Join-Path $Root 'frontend'
$Backend=Join-Path $Root 'research_backend_v18'
if(Test-Path $Backend){throw "拒绝覆盖现有后端：$Backend"}
New-Item -ItemType Directory -Force -Path $Root|Out-Null
if(-not(Test-Path $Front)){
 if(-not(Get-Command git -ErrorAction SilentlyContinue)){throw '需安装Git才能完整克隆五序'}
 & git clone 'https://github.com/meilin2026dh/pl5.git' $Front
 if($LASTEXITCODE -ne 0){throw '获取完整GitHub源码失败'}
 Push-Location $Front
 try{
  $Pinned='9eb9ec5ad542877680755bccf27345298ef7b99f'
  & git cat-file -e "$Pinned^{commit}"
  if($LASTEXITCODE -ne 0){throw '受审查的GitHub提交不存在'}
  & git switch -c 'pl5-v18-aan-fusion' $Pinned
  if($LASTEXITCODE -ne 0){throw '创建本地融合分支失败'}
 }finally{Pop-Location}
}
if(-not(Test-Path (Join-Path $Front 'src\pages\Workbench.tsx'))){throw 'GitHub源码缺少工作台'}
$Python=Get-Command python -ErrorAction SilentlyContinue
if(-not $Python){throw '缺少Python3.12'}
& $Python.Source (Join-Path $Source 'integration_tests\upgrade_github_overlay_v18.py') --github-root $Front
if($LASTEXITCODE -ne 0){throw '前端文件冲突，停止安装'}
Copy-Item -Recurse (Join-Path $Source 'research_backend') $Backend
foreach($sub in @('runtime','data\official_archive_v17','reports\v18')){
 New-Item -ItemType Directory -Force (Join-Path $Root $sub)|Out-Null
}
Write-Host "V1.8已复制至$Backend；未启用后台任务，未批准任何研究规则。"
