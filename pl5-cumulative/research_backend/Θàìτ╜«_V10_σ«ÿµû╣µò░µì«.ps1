# Explicitly enable development-only experimentation using an operator-verified CSV.
param([string]$ProjectRoot='D:\pl5', [Parameter(Mandatory=$true)][string]$OfficialCsv,
      [Parameter(Mandatory=$true)][string]$OfficialSource)
$ErrorActionPreference='Stop'
if(-not(Test-Path -LiteralPath $OfficialCsv -PathType Leaf)){throw 'CSV不存在'}
if(-not($OfficialSource.StartsWith('official:') -or $OfficialSource.StartsWith('https://'))){throw '必须填写核对后的官方公告来源'}
$runtime=Join-Path $ProjectRoot 'runtime'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
@{enable_development_audit=$true;official_csv=[System.IO.Path]::GetFullPath($OfficialCsv);official_source=$OfficialSource} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'v10_schedule.json') -Encoding UTF8
Write-Host '已开启V1.0定时开发集实验；实验数据源须由使用者持续更新与核验，不会自动进行开奖前封存或投注。'
