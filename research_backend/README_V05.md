# PL5 V0.5 — 自主科研与算法生长智能体（实验研究版）

本项目以V0.4完整源码为基础，保留基础过滤、历史时序反延续、跨空间映射、规则竞争、映射稳健性及10万注排序。
V0.5新增**定期公开科研信息检索→智能体假设登记→开发集滚动实验→影子规则→1至100注候选→新期开奖前预注册→开奖后核验**的可执行闭环。

> 严格边界：公平、独立开奖前提下，100注单期命中基线为0.1%，10期至少命中一次约0.9955%。任何历史模式不保证未来更不可能发生。100注排序不是校准的真实中奖概率。

## 本版功能与边界

| 功能 | V0.5状态 |
|---|---|
| 公开论文/仓库自动巡检 | 支持OpenAlex、arXiv、GitHub的官方接口；缺网或限流如实记录错误 |
| 论文与算法去重知识库 | SQLite、来源、日期、标题、摘要、主题、评分、试验台账 |
| 自动研究假设 | 本地白名单的指标×模式×时间窗口组合；不能把论文思想自动等同于有效过滤法 |
| 可选大模型论文分析 | 用户手动授权调用大模型API，摘要→方法/限制/可证伪假设卡，受限规则需本地校验 |
| 逐期独立于未来的滚动回测 | 仅用已知开奖历史、开发集统计，标注多重检验风险 |
| 固定K<=100注 | 可输出CSV；未发现证据时为可复现的随机基线打散 |
| 预注册与10期挑战核验 | 目标期号候选集在本地SQLite预先冻结，开奖后仅追加结果；提供10期窗口报告 |
| 定时执行 | Windows任务计划程序，每6小时巡检；不自动购买或投注；电脑关机不可运行 |
| 论文全文读写任意新算法 | **尚未实现**；目前为论文摘要分析＋受限研究规则。未来需隔离代码沙箱与人工准入 |

## Windows升级到D盘

1. 下载ZIP，解压到临时目录。
2. 双击根目录 `install_to_D_v05.bat`，确认脚本的来源及提示。脚本创建/升级 `D:\pl5`，对拟覆盖的旧源码先做备份；保留 `data`、`runtime`、`.venv`、`archive`、`research_reports`。
3. PowerShell：

```powershell
cd D:\pl5
uv sync --python 3.12 --extra agent --group dev
uv run pytest -q
uv run streamlit run phase2_app.py
```

Streamlit导航页选择 **05 自主科研智能体**。

### 开启定期科研扫描（显式启用）

```powershell
powershell -ExecutionPolicy Bypass -File .\启用_定时科研.ps1
# 默认每6小时执行1次，查日志 research_reports\schedule_latest.log
powershell -ExecutionPolicy Bypass -File .\停止_定时科研.ps1
```

默认的定时任务只做API检索、去重及本地受限假设合成；**不会自动发起付费大模型请求**。如果你明确希望自动做大模型论文分析，请先安装可选依赖、配置环境变量并接受API计费：

```powershell
uv sync --python 3.12 --extra agent --extra llm --group dev
$env:OPENAI_API_KEY='自行在当前会话注入，不要写进项目代码或上传给其他人'
uv run python research_cli.py analyze --limit 1
```

`analyze`对尚未分析的论文每次最多处理`--limit`篇；建议先手动运行，观察费用及输出质量。若自行设置 `PL5_ENABLE_PAID_LLM=1` 并为任务运行账户正确配置 `OPENAI_API_KEY`，定时任务才会调用付费分析，最多每轮2篇。

## 常用研究命令

```powershell
cd D:\pl5
uv run python research_cli.py scan
uv run python research_cli.py propose
uv run python research_cli.py status
# 可选：依赖OpenAI API密钥且会产生费用
uv run python research_cli.py analyze --limit 2

# 确认历史CSV真来自官方公告，再进行本地科研实验
uv run python research_cli.py evaluate --csv data\official_pl5.csv --official-source 'official:已人工核验中国体彩公告' --k 100
uv run python research_cli.py shadow --fingerprint <候选假设指纹>
uv run python research_cli.py rank --csv data\official_pl5.csv --official-source 'official:已人工核验中国体彩公告' --k 100

# 在尚未开奖的目标期号，封存最终100注及研究规则指纹（不可修改）
uv run python research_cli.py freeze --csv data\official_pl5.csv --official-source 'official:已人工核验中国体彩公告' --target-period <待开奖期号> --k 100

# 新一期开奖后更新官方数据CSV，并核验已封存的预测
uv run python research_cli.py settle --csv data\official_pl5.csv --official-source 'official:已人工核验中国体彩公告'
uv run python research_cli.py prospective
```

**重要：** `official:`为操作员的来源声明，不是技术验真；仍需人工核实原始公告。CSV必须有`period,number`两列，必须保留五位开奖号码前导零。

## 预注册研究局限

SQLite触发器防止通过普通UPDATE/DELETE修改记录，并在后台记录封存摘要；但本地数据库由用户掌握，仍可被删除、整体替换或绕过。**本地封存不构成不可篡改的第三方时间证明**。对于真正要验证“10期内命中”的目标，必须在开奖前独立留存候选号码、期号、时间和SHA256，并采用不受本研究者控制的时间戳/第三方托管。

## 当前验收范围

- 本地 Python 3.13 环境：**70项自动化测试通过**，含原有模块、离线模拟OpenAlex/arXiv/GitHub采集、论文假设入库、100注输出、LLM接口模拟、不可修改的本地预注册和10期统计。
- 尚未在本环境对真实API逐个联网实跑，LLM真实付费调用也尚未做过；Windows任务计划程序及Streamlit需在你机器本机验收。
- 不会从本会话直接操作`D:\pl5`，必须用部署脚本安装。
