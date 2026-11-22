param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$PackageRoot=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if(-not(Test-Path $Drive)){throw "盘符不存在：$Drive"}
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$Front=Join-Path $Root 'frontend'
$Backend=Join-Path $Root 'research_backend_v16'
$Vendor=Join-Path $Root 'github_vendor_v16'
foreach($item in @($Backend,$Vendor)){
  if(Test-Path $item){throw "目标目录已经存在，拒绝覆盖：$item"}
}
if(-not(Test-Path $Front)){
  if(-not(Get-Command git -ErrorAction SilentlyContinue)){throw '缺少Git，无法获取完整五序源码'}
  & git clone 'https://github.com/meilin2026dh/pl5.git' $Front
  if($LASTEXITCODE -ne 0){throw 'GitHub源码克隆失败'}
  Push-Location $Front
  try {
    $pin='9eb9ec5ad542877680755bccf27345298ef7b99f'
    & git cat-file -e "$pin^{commit}"
    if($LASTEXITCODE -ne 0){throw '已评审的固定提交不存在'}
    & git switch -c 'pl5-v16-integration' $pin
    if($LASTEXITCODE -ne 0){throw '安全集成分支创建失败'}
  } finally {Pop-Location}
}else{
  Write-Host '复用现有GitHub工作树；不自动fetch、pull、reset或覆盖用户改动。'
}
if(-not(Test-Path (Join-Path $Front 'src\pages\Workbench.tsx'))){throw '前端缺少五序Workbench.tsx'}
$Python=Get-Command python -ErrorAction SilentlyContinue
if(-not $Python){$Python=Get-Command py -ErrorAction SilentlyContinue}
if(-not $Python){throw '请先安装Python 3.12'}
& $Python.Source (Join-Path $PackageRoot 'integration_tests\upgrade_github_overlay_v16.py') --github-root $Front
if($LASTEXITCODE -ne 0){throw '存在无法安全合并的前端修改，已停止安装'}
Copy-Item -Recurse (Join-Path $PackageRoot 'research_backend') $Backend
Copy-Item -Recurse (Join-Path $PackageRoot 'github_vendor') $Vendor
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'runtime') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'reports\v16') | Out-Null
Write-Host "安装完成：$Backend。原始开奖数据、sqlite证据账本及旧版本未覆盖。"
Write-Host '下一步运行 验证_V16.ps1；未经人工审核，不会自动应用实验权重。'
