# PL5 V1.7 — 长期科研调度与官方数据归档

本版本在 V1.6 的 Python 自主科研与 ESSE 解空间雕塑引擎上，增加 **长期运行保障**。不改变原有彩票规则，不提供任何中奖保证，也不启用自动交易或自动批准算法。

## 已实现

- **周期性科研**：Windows Task Scheduler 注册每天固定的多个每日触发器，默认每6小时一次；修复旧版只设置1天 RepetitionDuration 的配置风险。系统关机或长期休眠不保证准时执行。
- **断点恢复**：V1.7 SQLite 分阶段记录同步、科研与最终报告，使用V1.0原有七步科研检查点；同一周期重复运行不重做成功阶段。可选择自动尝试恢复同配置的一个未完成旧周期。
- **并发保护**：Windows `msvcrt`、Linux `fcntl` 操作系统文件锁，避免同一台计算机同时执行多个科研周期；任务异常退出时由系统自动释放锁。
- **官方数据**：从固定的中国体育彩票排列五历史 API (彩种代码350133) 取数；日期、期号、五码及来源结构校验；增量合并旧历史，保留前导零，发现冲突即阻止覆盖；SHA256版本化历史快照，不将缓存静默当成新开奖。
- **容错**：官方接口临时网络故障时记录退化状态，仍允许独立的论文元数据研究；**本期未刷新官方数据时不做基于过期数据的新开发回测**。来源字段不等于第三方原产地加密证明。
- **科研状态展示**：只读HTTP诊断字段 `autonomous_research`、React `ResearchOpsV17` 面板，显示周期执行状态、失败原因、官方档案期号。
- **安全限制**：不自动执行论文/GitHub上的任意代码，不自动批准新算法，不自动投注；默认无付费LLM。

## 安装（Windows）

0. 前置：Git、Python 3.12、uv、Node.js 24、pnpm 11。正式执行新生成的Python代码仍需要单独Docker安全环境并人工审查。
1. 解压部署包，运行 `install_to_D_v17.bat`。会复制新后端至 `D:\pl5\research_backend_v17`，原有 `data`、`runtime`、旧版本后端不会覆盖。五序GitHub前端存在时使用原工作树；没有时安全克隆并固定到已审查的提交。存在用户改动冲突会拒绝自动修改。
2. 运行 `验证_V17.ps1`，验证V1.7新增用例，并在目标Windows系统上执行五序前端完整测试、类型检查和生产构建。
3. 分别运行 `启动_V17_科研后端.ps1`、`启动_V17_五序前端.ps1`，浏览器访问 `http://127.0.0.1:5173/workbench`，在“自主科研运行中心”查看状态。
4. **明确授权后**运行 `启用_V17_定时科研.ps1` 注册长期任务；存在旧版任务则要求先人工检查停用，不会替你覆盖已有调度。
5. 使用 `停止_V17_定时科研.ps1` 可禁用而不删历史数据。

### 手动启动一次科研周期

```powershell
cd D:\pl5\research_backend_v17
uv run python research_v17.py `
  --db D:\pl5\runtime\research_supervisor_v17.sqlite `
  --papers-db D:\pl5\runtime\autoresearch.sqlite `
  --archive D:\pl5\data\official_archive_v17 `
  once --live --sync-official --pages 2 --audit --recover-incomplete
```

查看任务状态：

```powershell
uv run python research_v17.py --db D:\pl5\runtime\research_supervisor_v17.sqlite --archive D:\pl5\data\official_archive_v17 status
```

> `--live` 意味着本次允许联网调用预设学术元数据 API；`--sync-official` 调用固定官方接口。`--audit` 仅运行历史开发集实验，不构成前向独立证据。外部服务会因限流、网络和接口变化发生失败。

### 完全离线演示（无需联网）

```powershell
cd D:\pl5\research_backend_v17
uv run python research_v17.py --db runtime\v17_demo.sqlite --papers-db runtime\papers_demo.sqlite --archive data\v17_demo_official once --offline-fixture examples\v10_demo_papers.json --cycle-key offline-demo-1
```

## 数据模型

`D:\pl5\data\official_archive_v17\index.json` 指向带SHA256版本名的 `snapshots/<hash>.json`，并生成 `official_history.csv`。历史已存在的期号或日期出现不一致时禁止覆盖。官方历史 API 单次支持最多20页（每页100期），每日增量默认2页；较早历史需从历史归档逐步积累，**不是已有全量历史**。

科研周期与阶段存储在 `runtime/research_supervisor_v17.sqlite`，文献和假设仍进入原有 `runtime/autoresearch.sqlite`。每个周期按UTC六小时桶命名，采用固定配置签名；无法用新配置偷偷覆盖旧研究。数据库可追溯但**不是不可篡改第三方时间证明**。勿与开奖现场事实混淆。

## 项目边界

本版实现的是**受约束、可恢复的科研调度**。仍不能在完全无人监护情况下忠实理解和复现任意科研论文，不能确保任何新算法具有预测价值。公平独立的排列五中，每期从10万注保留100注，其精确命中概率仍是0.1%；连续10期至少一次约0.996%。

此次发布包括前端增量源码与此前经过审核的GitHub模块归档，并不将完整GitHub前端源码复制进压缩包；安装器会优先复用 `D:\pl5\frontend`，不存在则从 `meilin2026dh/pl5` 获取。不要将未经过Windows实测的当前环境测试当成Windows验收完成。
