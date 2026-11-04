param([string]$Root = 'D:\pl5')
$ErrorActionPreference = 'Stop'
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Test-Path (Split-Path -Qualifier $Root))) { throw "目标驱动器不存在: $Root" }
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$Repo = Join-Path $Root 'frontend'
$Backend = Join-Path $Root 'research_backend_v13'
$Vendor = Join-Path $Root 'github_vendor_v13'
if (Test-Path $Backend) { throw "已有V1.3后端目录，拒绝覆盖：$Backend" }
if (Test-Path $Vendor) { throw "已有GitHub源文件归档，拒绝覆盖：$Vendor" }
if (-not (Test-Path $Repo)) {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
      throw '没有Git。请先安装Git，或将完整仓库自行复制到D:\pl5\frontend再重试。'
    }
    & git clone 'https://github.com/meilin2026dh/pl5.git' $Repo
    if ($LASTEXITCODE -ne 0) { throw 'GitHub克隆失败。你也可以手工复制仓库至frontend后再重试。' }
    # Freeze the cloned source to the GitHub revision used for review.
    Push-Location $Repo
    try {
        $Pinned = '9eb9ec5ad542877680755bccf27345298ef7b99f'
        & git cat-file -e "$Pinned^{commit}" 2>$null
        if ($LASTEXITCODE -ne 0) { throw "未找到审核时的GitHub版本 $Pinned，请手工核对新版本" }
        & git checkout -b 'pl5-v13-integration-base' $Pinned
        if ($LASTEXITCODE -ne 0) { throw '无法固定GitHub源版本' }
    } finally { Pop-Location }
} elseif (-not (Test-Path (Join-Path $Repo 'src\pages\Workbench.tsx'))) {
    throw "$Repo不是五序PL5完整仓库，拒绝安装";
} else {
    Write-Host '已发现用户自己的GitHub前端目录；不会执行pull、reset或checkout。'
}
$Python = Get-Command python -ErrorAction SilentlyContinue
if ($Python) { $PythonBin='python' }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $PythonBin='py' }
else { throw '没有Python，无法运行安全源码合并脚本。现有文件未被覆盖。' }
# First check patch compatibility against a throwaway copy of the two actual targets.
# The upgrade script refuses unrecognized source changes.
& $PythonBin (Join-Path $PackageRoot 'integration_tests\upgrade_github_overlay_v13.py') --github-root $Repo
if ($LASTEXITCODE -ne 0) { throw '前端补丁失败。已保留旧文件及相关备份。' }
Copy-Item (Join-Path $PackageRoot 'research_backend') $Backend -Recurse
Copy-Item (Join-Path $PackageRoot 'github_vendor') $Vendor -Recurse
Write-Host 'PL5 V1.3已部署：'
Write-Host "  五序完整GitHub源码: $Repo"
Write-Host "  Python研究后端:      $Backend"
Write-Host "  GitHub原版4模块备份: $Vendor"
Write-Host '原来的D:\pl5文件及runtime、data未被修改。请运行V1.3验证脚本。'
