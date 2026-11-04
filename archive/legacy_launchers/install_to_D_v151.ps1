param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$PackageRoot=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if(-not(Test-Path $Drive)){throw "盘符不存在：$Drive"}
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$Front=Join-Path $Root 'frontend'
$Backend=Join-Path $Root 'research_backend_v151'
$Vendor=Join-Path $Root 'github_vendor_v151'
foreach($item in @($Backend,$Vendor)){
  if(Test-Path $item){throw "已有目录，为避免覆盖停止：$item"}
}
if(-not(Test-Path $Front)){
  if(-not(Get-Command git -ErrorAction SilentlyContinue)) {throw '请先安装Git，或手动克隆GitHub仓库至D:\pl5\frontend'}
  & git clone 'https://github.com/meilin2026dh/pl5.git' $Front
  if($LASTEXITCODE -ne 0){throw 'GitHub仓库克隆失败'}
  Push-Location $Front
  try {
    $pin='9eb9ec5ad542877680755bccf27345298ef7b99f'
    & git cat-file -e "$pin^{commit}"
    if($LASTEXITCODE -ne 0){throw '已评审的GitHub基准提交不存在，请手动核查'}
    & git switch -c 'pl5-v151-integration' $pin
    if($LASTEXITCODE -ne 0){throw '建立安全集成分支失败'}
  } finally {Pop-Location}
} else {
  Write-Host '复用D盘现有五序GitHub仓库；不自动pull、reset或checkout。'
}
if(-not(Test-Path (Join-Path $Front 'src\pages\Workbench.tsx'))){throw '前端并非完整五序源代码，已中止'}
$Python=Get-Command python -ErrorAction SilentlyContinue
if(-not $Python){$Python=Get-Command py -ErrorAction SilentlyContinue}
if(-not $Python){throw '需要Python环境才能执行安全源码接入'}
& $Python.Source (Join-Path $PackageRoot 'integration_tests\upgrade_github_overlay_v151.py') --github-root $Front
if($LASTEXITCODE -ne 0){throw 'GitHub集成检查失败：发现非预期修改，请人工合并，不覆盖'}
Copy-Item -Recurse (Join-Path $PackageRoot 'research_backend') $Backend
Copy-Item -Recurse (Join-Path $PackageRoot 'github_vendor') $Vendor
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'runtime') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'reports\v151') | Out-Null
Write-Host "已创建$Backend，五序页面已加入科研状态看板。"
Write-Host '后续：先运行 验证_V151.ps1，再分别运行两个启动脚本。'
Write-Host '没有自动开启定时科研、自动审批或自动购彩。'
