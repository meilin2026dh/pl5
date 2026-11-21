param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Source=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if(-not(Test-Path $Drive)){throw "目标盘符不存在：$Drive"}
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$Front=Join-Path $Root 'frontend'
$Backend=Join-Path $Root 'research_backend_v17'
if(Test-Path $Backend){throw "拒绝覆盖已存在的研究后端：$Backend"}
if(-not(Test-Path $Front)){
  if(-not(Get-Command git -ErrorAction SilentlyContinue)){throw '缺少Git，无法获取GitHub五序前端'}
  & git clone 'https://github.com/meilin2026dh/pl5.git' $Front
  if($LASTEXITCODE -ne 0){throw 'GitHub五序克隆失败'}
  Push-Location $Front
  try {
    $Pinned='9eb9ec5ad542877680755bccf27345298ef7b99f'
    & git cat-file -e "$Pinned^{commit}"
    if($LASTEXITCODE -ne 0){throw '审查过的五序提交缺失'}
    & git switch -c 'pl5-v17-fusion' $Pinned
    if($LASTEXITCODE -ne 0){throw '创建GitHub融合分支失败'}
  } finally {Pop-Location}
}
if(-not(Test-Path (Join-Path $Front 'src\pages\Workbench.tsx'))){throw '缺少GitHub五序工作台源文件'}
$PY=Get-Command python -ErrorAction SilentlyContinue
if(-not $PY){throw '需要系统可调用的Python3；请先安装Python3.12'}
& $PY.Source (Join-Path $Source 'integration_tests\upgrade_github_overlay_v17.py') --github-root $Front
if($LASTEXITCODE -ne 0){throw '前端源码存在冲突，未执行覆盖'}
Copy-Item -Recurse (Join-Path $Source 'research_backend') $Backend
foreach($Dir in @('runtime','data\official_archive_v17','reports\v17')){
  New-Item -ItemType Directory -Force -Path (Join-Path $Root $Dir)|Out-Null
}
Write-Host "V1.7部署完成：$Backend"
Write-Host '不会自动启用计划任务、付费API、执行生成代码或自动审批。先运行 验证_V17.ps1。'
