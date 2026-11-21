param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$PackageRoot=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if(-not(Test-Path $Drive)){throw "不存在的盘符：$Drive"}
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$Front=Join-Path $Root 'frontend'
$Backend=Join-Path $Root 'research_backend_v15'
$Vendor=Join-Path $Root 'github_vendor_v15'
foreach($p in @($Backend,$Vendor)){if(Test-Path $p){throw "为保护已有代码拒绝覆盖：$p"}}
# Install the full reviewed GitHub frontend if it is not already present.
if(-not(Test-Path $Front)){
  if(-not(Get-Command git -ErrorAction SilentlyContinue)){throw '请先安装Git或手动把五序仓库复制到frontend'}
  & git clone 'https://github.com/meilin2026dh/pl5.git' $Front
  if($LASTEXITCODE -ne 0){throw '克隆GitHub仓库失败'}
  Push-Location $Front
  try {
    $Pin='9eb9ec5ad542877680755bccf27345298ef7b99f'
    & git cat-file -e "$Pin^{commit}" 2>$null
    if($LASTEXITCODE -ne 0){throw 'GitHub源码版本不符合已评审的版本，停止安装'}
    & git switch -c 'pl5-v15-fusion' $Pin
    if($LASTEXITCODE -ne 0){throw '无法切换GitHub集成分支'}
  } finally {Pop-Location}
} else {Write-Host '已发现五序源码，保持其Git仓库、历史修改和原方案不变。'}
if(-not(Test-Path (Join-Path $Front 'src\pages\Workbench.tsx'))){throw '前端目录不完整，拒绝安装'}
if(Get-Command python -ErrorAction SilentlyContinue){$Py='python'}
elseif(Get-Command py -ErrorAction SilentlyContinue){$Py='py'}
else{throw '安装需Python和uv'}
& $Py (Join-Path $PackageRoot 'integration_tests\upgrade_github_overlay_v14.py') --github-root $Front
if($LASTEXITCODE -ne 0){throw 'GitHub集成补丁不一致：请先审查用户修改，不强制覆盖'}
Copy-Item -Recurse (Join-Path $PackageRoot 'research_backend') $Backend
Copy-Item -Recurse (Join-Path $PackageRoot 'github_vendor') $Vendor
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'runtime') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'reports\v15') | Out-Null
Write-Host "PL5 V1.5源码部署完成：$Backend"
Write-Host '请运行启动_V15_验证.ps1。未擅自启用后台任务、自动审批或自动购彩。'
