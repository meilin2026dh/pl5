param([string]$Root = 'D:\pl5')
$ErrorActionPreference = 'Stop'
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Test-Path 'D:\')) { throw 'D: 盘不存在。请确认磁盘或使用 -Root 指定目录。' }
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$Repo = Join-Path $Root 'frontend'
$Backend = Join-Path $Root 'research_backend_v12'
if (Test-Path $Backend) { throw "为保护现有程序，不覆盖已存在的目录：$Backend。请先备份或选择新的Root。" }
if (-not (Test-Path $Repo)) {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw '请先安装Git，然后重新运行本脚本。' }
    & git clone --depth 1 'https://github.com/meilin2026dh/pl5.git' $Repo
    if ($LASTEXITCODE -ne 0) { throw 'GitHub克隆失败。未覆盖旧版Python项目。' }
} else {
    if (-not (Test-Path (Join-Path $Repo 'src\pages\Workbench.tsx'))) {
        throw "已有目录$Repo不是五序PL5前端，已停止避免覆盖。"
    }
    Write-Host '使用现有frontend目录；不会自动git pull或重置任何修改。'
}
Copy-Item (Join-Path $PackageRoot 'research_backend') $Backend -Recurse
$Python = 'python'
if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    $Python = 'py'
    if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) { throw '没有发现Python。后端已复制，但前端补丁尚未应用。' }
}
& $Python (Join-Path $PackageRoot 'integration_tests\apply_github_overlay.py') --github-root $Repo
if ($LASTEXITCODE -ne 0) { throw 'Github五序前端源码与预期锚点不兼容，请查阅更新说明。' }
Write-Host ''
Write-Host 'PL5 V1.2 融合代码已经复制（未自动安装依赖或启动长期后台服务）。'
Write-Host "GitHub前端: $Repo"
Write-Host "Python科研后端: $Backend"
Write-Host '先阅读 V12_部署与接口说明.md，再分别启动后端和前端。'
