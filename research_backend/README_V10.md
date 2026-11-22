# PL5 V1.0 — 自主科研、断点恢复与可核验候选包

**研究用途。不是彩票预测优势的证明或投注程序。** 公平独立开奖且每期恰好选100注时，单期命中率为100/100000=0.1%，连续10期至少命中一次的理论概率为 `1-(1-0.001)^10≈0.9955%`。抽象论文线索、低频模式、映射空间与自动生成算法均不能自动改变这一基线。

## 重要功能

1. **七步科研循环** `discover → hypothesize → ingest → invent → propose_python → audit → review`；研究任务和各步骤状态保存于 `runtime/autoresearch.sqlite`。数据库按任务ID幂等恢复；失败步骤可重试，成功步骤不重复。若版本源码发生变化，禁止悄悄跨版本续跑。
2. **安全默认值**：需要主动指定 `--live` 才访问公开学术接口；无人值守禁止付费LLM、自动执行外部Python代码、自动批准研究成果和投注。论文元数据属不可信输入。
3. **科研任务预算**：每轮限制检索主题、来源请求数、处理文献、生成公式及Python候选。`metadata_requests_max` 是计划请求数量的上界而非API运营商的实收费；付费模型次数固定为0。
4. **开发集证伪（可选）**：必须显式提供人工核验的官方CSV及出处，任务绑定解析后的历史序列摘要；调用原有V0.6 `full_audit`。这仍属于开发集实验，不是未来预测证据。
5. **候选集合绑定封存**：对当前 `shadow` 规则运行原有 `rank_100`，封存1–100注、原始CSV字节SHA256、源代码指纹、NumPy/Python版本、规则快照、研究性评分证据、目标期号；可从同一CSV和封存规则重新计算全部候选。
6. **只读中控页面**：`10 自主科研V1中控台`，展示任务状态、步骤、预算及候选包索引。不从网页自动启动无人值守任务。
7. **Windows本机定时任务**：`启用_V10_定时科研.ps1` 必须由操作员显式执行，默认6小时一次。断网全部来源失败时记录失败并于下次恢复，保留检查点；旧版任务存在时拒绝自动创建重叠任务。

## 兼容性与数据保护

V0.1–V0.9项目页面、CLI、过滤算法、映射研究和SQLite结构保留。升级脚本仅复制程序文件，并在覆盖前备份；不会覆盖 `data/`、`runtime/`、`.venv/`、自定义 `config/`、已有研究报告等目录。新安装可保留一个**明确标注为合成演示**的CSV样例。

## Windows安装

下载完整版ZIP，解压后执行根目录的 `install_to_D_v10.bat`。在PowerShell中：

```powershell
cd D:\pl5
uv sync --python 3.12 --extra agent --extra fulltext --group dev
uv run pytest -q
uv run python research_v10.py demo
uv run streamlit run phase2_app.py
```

首次运行 `uv sync` 需要安装uv并允许联网获取依赖。源码及自动化测试已在开发环境验证，**尚未在用户Windows机器实际安装或运行Docker**。

## 操作1：运行不联网的可恢复科研演示

```powershell
cd D:\pl5
uv run python research_v10.py run --offline-fixture examples\v10_demo_papers.json --max-documents 2
uv run python research_v10.py status
```

输出的 `run_id` 可用于续跑，必须使用完全相同的参数：

```powershell
uv run python research_v10.py run --offline-fixture examples\v10_demo_papers.json --max-documents 2 --run-id run_XXXXXXXX
```

演示论文是合成虚构元数据，绝非真实论文或真实彩票开奖。

## 操作2：显式访问公开文献元数据

```powershell
uv run python research_v10.py run --live --resume-latest --topics "sequential multiple testing,randomness testing" --providers "openalex,arxiv" --max-requests 6 --max-documents 3
```

网络请求可能因限速或接口变更失败。这时不会凭空捏造论文，也不会自动使用昂贵的模型进行研究。任务记录在SQLite；下次同配置运行 `--resume-latest` 可以尝试恢复。

## 操作3：接入人工核验的官方开奖CSV进行开发集审查

CSV格式 `period,number`，必须保留五位号码的前导零，期号须数字且按升序排列，不能含缺失或重复。**程序本身不能验证用户填写的URL一定是官方来源**。

```powershell
uv run python research_v10.py run --live --resume-latest --official-csv data\official_history.csv --official-source "official:已人工核对的中国体彩网公告及采集日期" --audit
```

如果不提供 `--audit`，仍会自动生成研究候选，但**不会把合成数据回测结果当成科学证据**。

## 操作4：对当期100注以内的候选集合生成可复算封存包

须先在原有系统将人工选择的规则登记为 `shadow`。生成：

```powershell
uv run python research_v10.py seal --official-csv data\official_history.csv --official-source "official:已核对的公告来源" --period 20261234 --k 100
```

验证（将路径替换为上一步返回的包名）：

```powershell
uv run python research_v10.py verify-seal --packet research_reports\v10_commits\<包名>.json --official-csv data\official_history.csv --require-ledger
```

`--period 20261234` 只是格式示例，**不表示该期实际存在或尚未开奖**。没有任何 `shadow` 规则时，默认禁止伪装成已有过滤依据；可显式加 `--allow-empty-baseline` 生成用于软件验证的随机基线集合。

封存包返回 `manifest_sha256`，可以由用户**在开奖之前**提交第三方可信时间戳/公开追加式日志保存回执。V1.0未集成也不能核实第三方可信时间证明，本地系统时间和SQLite中的SHA256都不足以单独证明“开奖前已封存”。

## 操作5：显式启用长期科研巡检

请先避免旧版任务与新版任务并发（如果存在旧版，手工执行 `停止_定时科研.ps1`）：

```powershell
powershell -ExecutionPolicy Bypass -File .\启用_V10_定时科研.ps1
```

如希望每轮同时做开发集实验，须主动配置并维护经核验的历史CSV：

```powershell
powershell -ExecutionPolicy Bypass -File .\配置_V10_官方数据.ps1 -OfficialCsv "D:\pl5\data\official_history.csv" -OfficialSource "official:逐期核验来源与日期"
```

不希望任务继续执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\停止_V10_定时科研.ps1
```

**电脑关机时本地任务不会持续研究；这不是云端后台服务。** 当前V1.0不会自动更新官方CSV，需要用户维护数据或后续实现经过人工授权的官方同步适配器。

## 科学与安全边界

- V1.0闭环处理的是学术**元数据/摘要**及保守的算法模板，不能声称自动复现所有论文的完整数学方法。旧版V0.6/V0.8的全文研究、Docker代码审查仍作为独立的人工触发功能保留。
- 新算法只进入研究候选库。工程测试通过≠具有预测优势；不能自动开启正式排名、开启投注或保证10期内中奖。
- `run` 产生的开发集p值不能当作独立前向证据。要验证是否超越随机基线，必须由事前锁定的模型在真实未来开奖上持续、完整地验证，并进行多重检验控制。
- 本地SQLite检查点并非防管理员篡改的审计日志；要构成可信的开奖前证据还需要第三方时间凭证、官方来源及模型与候选表一致性审查。
- 每次扫描的默认文献相关性仅是选题优先级，不是“能预测开奖号码”的概率。
