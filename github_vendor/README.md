# 从meilin2026dh/pl5直接复制的原版模块

此目录保存四个经Git blob SHA核对的真实TypeScript源文件，仅用于独立审计、交叉实验、离线阅读和恢复。

它不包含完整React项目。完整五序GitHub工程会由安装脚本在Windows端克隆至`D:\pl5\frontend`（若已存在，则保留现有版本）。

离线冒烟测试：在Node22+运行`node --experimental-strip-types github_vendor/tests/offline-smoke.mjs`。
