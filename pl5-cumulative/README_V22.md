# PL5 V2.2 — 受约束自主算法工程、自动反例与跨语言复核

**基础：** V2.1 全部能力保留；V2.2 不修改 GitHub 五序基础过滤模型，不自动修改任何正式 ESSE 刀具。

## 这一版实际做了什么

1. **角色协同的代码生成：** 从 V2.1 研究项目关联的、经过原文定位的 V2.0 方法卡读取研究主题。识别出明确可实施的数学特征时，使用**五个受限算法族**之一自动生成两套结构不同的 Python `score_batch(history,candidates)` 和一套 Node.js `scoreBatch(history,candidates)`；识别不出方法就返回 `requires_explicit_method_review`，绝不捏造“论文原算法”。
2. **安全登记与源代码溯源：** 生成代码经过 AST 静态检查和 SHA256 固定，自动填充 V2.1 两路工程角色与红队检查计划。SQLite 新增不可变的 `v22_generated` 记录，每个项目仅准生成一版。
3. **执行式反例实验：** 经明确 `--allow-docker` 同意后，使用不可写入宿主的隔离容器运行零历史、全零/全九、前导零、重复历史、候选排列置换和可选完整十万注测试；比较每一个候选的**数值分数**，而不只是 Top-K 是否相同。
4. **异构复核：** CPython 3.12 和 Node.js 24 使用不同容器运行。两套 Python、Node 实现及宿主内置**可信公式参考**之间逐值比较。后者只计算事先明确的数学定义，绝不在宿主执行候选源码；即使所有实现共同算错，也可能被可信公式参考挡下。
5. **审计门禁：** 运行结果写入不可变 `v22_evaluations`，保存数据指纹、源代码指纹、全部检查结果与 SHA256。工程通过也不代表论文忠实复现或彩票预测有效，不自动注册正式 ESSE 刀具。
6. **五序只读研究看板：** 新增 `GET /api/esse/research-v22` 与 React 只读面板，查看生成/验证数量、数值一致性及“未经预测验证”状态。
7. **每6小时研究调度：** 继承旧版官方数据归档、论文检索、能力生长与V2.1计划创建，增加 V2.2 **离线受限源码生成**。计划任务不启动 Docker、不调用付费模型、不进行正式发布。

## 能力上限与研究诚实性

- 目前的五个自动工程算法族：`digit_sum`、`span`、`adjacent_energy`、`lag_overlap`、`digit_frequency`。它们是受限的工程迁移模板，不是无限开放的自主论文算法发明；不同算法族可以扩展，但不会为凑数量伪造新方法。
- 三路编译器共享统一数学定义，所以称“**跨语言工程复核**”，不称“独立发现同一科学原理”。
- 静态源代码检查不是安全证明；只允许生成的 Node 模板，Python 执行只允许容器隔离。容器须独立安装与验证，Docker 缺失时 fail-closed。
- 本地哈希不可证明算法在开奖前已存在，更不能证明未来号码可预测。公平独立条件下100注一等直选单期概率仍为0.1%。
- V2.2的 Docker 真实运行、Windows、真实API联机、完整 GitHub React 生产构建与长期前向数据尚未在当前环境验收。

## Windows安装

下载V2.2完整压缩包，解压后双击 `install_to_D_v22.bat`，默认安装至 `D:\pl5\research_backend_v22`，前端复用 `D:\pl5\frontend`。安装器不删除旧版后端、归档、用户数据。若前端被用户修改，增量安装会失败并保留用户文件，不强制复位仓库。

然后在PowerShell运行：

```powershell
cd D:\pl5
powershell -ExecutionPolicy Bypass -File .\验证_V22.ps1
powershell -ExecutionPolicy Bypass -File .\启动_V22_科研后端.ps1
```

另开窗口运行 `启动_V22_五序前端.ps1`，打开 `http://127.0.0.1:5173/workbench`。页面增加 **自主算法工程与异构复核** 只读面板。

### 研究CLI

```powershell
cd D:\pl5\research_backend_v22
$DB='D:\pl5\runtime\autoresearch.sqlite'

# 查看已有V2.1研究计划；或先运行V2.0导入与方法卡登记
uv run --no-sync python research_v21.py --db $DB status

# 选择能识别方法族的项目，自动生出三套源码；不触发容器
uv run --no-sync python research_v22.py --db $DB generate --project <PROJECT_ID>

# 文献题目不足以识别具体算法时，人工明确选择受限族
uv run --no-sync python research_v22.py --db $DB generate --project <PROJECT_ID> --family lag_overlap

# 无人值守科研任务只生成新候选，不执行它们
uv run --no-sync python research_v22.py --db $DB auto-generate --limit 3
uv run --no-sync python research_v22.py --db $DB status --project <PROJECT_ID>

# 需要Docker Desktop、独立Docker镜像及本次明确批准：实际两种容器和全域数值复核
uv run --no-sync python research_v22.py --db $DB evaluate --project <PROJECT_ID> --allow-docker --complete-domain
```

容器运行时需要 `python:3.12-alpine` 与 `node:24-alpine` 镜像；默认网络禁用、非root、只读挂载、CPU/内存限制及执行超时。**请不要直接执行从外部论文或GitHub复制来的代码**。正式实用之前，建议审查镜像、Docker Desktop配置和Windows端沙箱限制。

### 定时科研

停用旧版任务并验收通过后才执行 `启用_V22_定时科研.ps1`。它按照每天00:10/06:10/12:10/18:10的时间触发本地研究流程；电脑关机期间不提供云端持续研究。停止用 `停止_V22_定时科研.ps1`。

## 核心源文件

- `research_backend/autoresearch/collaboration_v22.py`：受限编译、双语异构容器、数值级反例和不可变数据库。
- `research_backend/research_v22.py`：生成/自动生成/验收/状态CLI。
- `research_backend/tests/test_collaboration_v22.py`：模板、门禁、验证与故障注入专项测试（使用显式模拟执行器，不能当成真实Docker验收）。
- `research_backend/tests/test_collab_http_v22.py`：真实本地HTTP只读接口测试。
- `github_overlay/src/components/ResearchCollabV22.tsx`：研究可视化面板。
- `integration_tests/upgrade_github_overlay_v22.py`：安全、幂等的GitHub前端补丁。

## 溯源

本版在V2.1源码上增加模块，沿用同一个 SQLite 科研数据库及原有数据和代码。测试清单与局限见 `V22_架构与验收报告.md`。
