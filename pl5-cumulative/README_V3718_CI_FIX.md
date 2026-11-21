# PL5 V3.7.18 CI Hotfix — 跨平台发布验收修复

本包在 **PL5_V3718_Full.zip** 完整累计源码上做无损增量，保留旧科研代码和证据文件。

## 改动

1. `research_backend/pyproject.toml`: 显式发现 `pailie5`、`autoresearch` 包，解决 Windows/Linux pip editable 安装失败。
2. `vitest.config.ts`: 只运行 Web 应用直属测试，历史迁移的相对目录测试交给独立集成验证；重计算测试超时20秒。
3. `.gitattributes`: 对受 SHA256 保护的历史代理和源文件固定 Git LF 检出。
4. `integration_tests/upgrade_github_overlay_v19.py` 至 `v22.py`: 原文写入改为原始 UTF-8 字节写入，防止 Windows CRLF 改写后安装器把合法发布文件误判为已修改。
5. `integration_tests/test_windows_upgrade_line_endings_v3718.py`: Windows CRLF 转换模拟回归4项。测试先失败，修复后全部通过。
6. `.github/workflows/research-backend.yml`: 在 GitHub Linux 与 Windows Python 3.12 下安装，先跑历史集成，再跑完整科研后端回归。

## 已进行的实际测试

- Linux 本地（Python 3.13）新增 Windows 换行模拟：4/4通过。
- Linux 本地历史集成：33/33通过。
- Linux 本地完整科研后端：877/877通过（144.09秒）。
- 所有9个修改或新增源码文件 Git Blob SHA 与 GitHub 研究分支一致。

**远端 CI 的准确状态以 GitHub Actions 实际运行输出为准**。这份报告不把尚未结束的远端 Windows 测试说成通过。没有在用户自己的 `D:\pl5` 机器上执行安装，不宣称有彩票预测优势。

## 使用

- 新安装请优先使用本次完整累计包。
- 已有本轮此前提供的 `PL5_V3718_Full.zip` 可用 CI 修复增量补丁覆盖同名文件。
- 仍应自行复核 GitHub PR #3 及 Actions 日志，在未取得 Windows + Linux 全绿前不合并 `main`。
