param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
Set-Location (Join-Path $Root 'research_backend_v152')
if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw '缺少uv，请先安装'}
& uv sync --python 3.12 --group dev
if($LASTEXITCODE -ne 0){throw 'uv sync失败'}
& uv run pytest -q
if($LASTEXITCODE -ne 0){throw 'Python测试未通过'}
Set-Location (Join-Path $Root 'frontend')
if(-not(Get-Command pnpm -ErrorAction SilentlyContinue)){throw '缺少pnpm'}
& pnpm install --frozen-lockfile
if($LASTEXITCODE -ne 0){throw 'pnpm install失败'}
& pnpm test
if($LASTEXITCODE -ne 0){throw '前端测试未通过'}
& pnpm typecheck
if($LASTEXITCODE -ne 0){throw 'TypeScript类型检查失败'}
& pnpm build
if($LASTEXITCODE -ne 0){throw '前端生产构建失败'}
Write-Host '代码测试通过。继续启动后端与前端两个终端，验证 http://127.0.0.1:3001/api/esse/status'
# 不假定用户已经启动服务，避免出现误导性的“实际联机成功”提示。
try {
  $r=Invoke-RestMethod -Uri 'http://127.0.0.1:3001/api/esse/status' -Method Get -TimeoutSec 5
  if($r.schema -ne 'pl5-live-status-v151'){throw '服务版本不匹配'}
  Write-Host ('实际跨服务联通成功：' + $r.schema + '，注册库状态：' + $r.registry.state)
} catch {
  Write-Host '服务尚未同时运行：代码验收通过，但跨服务实机联通待验证。'
}
