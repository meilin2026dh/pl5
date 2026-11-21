param([string]$Root = 'D:\pl5')
$ErrorActionPreference='Stop'
$PackageRoot=Split-Path -Parent $MyInvocation.MyCommand.Path
$Drive=Split-Path -Qualifier $Root
if (-not (Test-Path $Drive)) { throw "不存在的盘符：$Drive" }
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$Front=Join-Path $Root 'frontend'
$Backend=Join-Path $Root 'research_backend_v14'
$Vendor=Join-Path $Root 'github_vendor_v14'
foreach($dest in @($Backend,$Vendor)) {
 if(Test-Path $dest) {throw "目标已存在，拒绝覆盖：$dest"}
}
if (-not (Test-Path $Front)) {
 if(-not (Get-Command git -ErrorAction SilentlyContinue)) { throw '需要Git来克隆完整Github源码' }
 & git clone 'https://github.com/meilin2026dh/pl5.git' $Front
 if($LASTEXITCODE -ne 0) { throw 'GitHub下载失败。请检查网络后重试，或先自行将仓库复制到frontend。' }
 Push-Location $Front
 try {
  $Revision='9eb9ec5ad542877680755bccf27345298ef7b99f'
  & git cat-file -e "$Revision^{commit}" 2>$null
  if($LASTEXITCODE -ne 0) { throw '未找到已经审阅的GitHub提交；请人工验证仓库新版本' }
  & git switch -c 'pl5-v14-integration' $Revision
  if($LASTEXITCODE -ne 0) { throw '无法切换到集成分支' }
 } finally {Pop-Location}
} else {Write-Host '现有frontend已保留，不执行pull、reset或checkout。'}
if (-not (Test-Path (Join-Path $Front 'src\pages\Workbench.tsx'))) {
 throw 'frontend不包含完整五序GitHub工程，拒绝继续'
}
if (Get-Command python -ErrorAction SilentlyContinue) {$Py='python'}
elseif(Get-Command py -ErrorAction SilentlyContinue) {$Py='py'}
else {throw '需要Python 3.12及uv'}
& $Py (Join-Path $PackageRoot 'integration_tests\upgrade_github_overlay_v14.py') --github-root $Front
if ($LASTEXITCODE -ne 0) {throw 'GitHub接入补丁失败，未覆盖已有Python研发目录。'}
Copy-Item -Recurse (Join-Path $PackageRoot 'research_backend') $Backend
Copy-Item -Recurse (Join-Path $PackageRoot 'github_vendor') $Vendor
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'runtime') | Out-Null
Write-Host "V1.4 安装完毕：$Backend"
Write-Host '原有data、runtime、旧版后端均已保留。请运行 启动_V14_验证.ps1 进行本机验收。'
