param([string]$Root='D:\pl5')
$ErrorActionPreference='Stop'
$Backend=Join-Path $Root 'research_backend_v26'
if (-not (Test-Path $Backend)) { throw '请先运行install_to_D_v26.bat' }
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw '需要Python3.12与uv' }
Set-Location $Backend
& uv sync --python 3.12 --group dev
if ($LASTEXITCODE -ne 0) { throw '安装依赖失败' }
& uv run python -m pytest -q tests/test_highdim_v26.py tests/test_hdse_registry_v26.py tests/test_http_hdse_v26.py tests/test_representation_v25.py tests/test_http_spaces_v25.py
if ($LASTEXITCODE -ne 0) { throw '新旧专项测试未通过' }
& uv run python research_v26.py propose --maximum 6 --report 'examples\v26_install_proposals.json'
if ($LASTEXITCODE -ne 0) { throw '算法提案失败' }
Write-Host 'V2.6科研专项验证通过。尚需另行验证真实官方数据与长时间科研运行。'
