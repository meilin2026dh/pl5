# PL5 V1.5 — 自主算法竞争与动态进化研究版

版本日期：2026-11-01。V1.5以V1.4为源码基线，**不删除以前各版本的实验功能**。核心变更是增加可重复运行、可审计的算法竞争、受限DSL候选规则创建和规则健康暂停。当前没有证明提高排列五的实际命中率。

## 已实现

- **受约束算法自动生长**：论文/研究文本通过现有 `autoresearch.novelty_v07` 形成指标表达式；只解释事先授权的DSL，不执行下载的Python；使用纯Python与NumPy交叉验证，分析历史近期的时序反延续，最多提交5条待审核候选；相同规则按签名去重。未触发、全删、超剔除比例均拒绝注册。**不会自动批准候选**。
- **持续条件体检**：从V1.4不可变10万位规则掩码与批准状态读取，逐条计算剔除比例、与其他已批准规则的重叠数量、边际新增过滤数、历史误删次数与相同规则的冻结测试证据；保留原始来源大底隔离。附可复现JSON报告。
- **带多重检验控制的自动暂停（可选）**：每条规则只在冻结截止日之后的完整、互不重叠样本块上执行“删掉实际开奖号码是否异常偏多”的单侧二项检验。错误预算对规则序号和时间块分别采用求和不超过1的分配；即使每天多次扫描同一完整区间，不会因重复扫描累计增加本算法的统计显著性。强烈反证只会**暂停已经人工批准的实验刀**，不会改变未经验证的算法为“预测算法”。恢复需要非创建者提供明确的审查说明。
- **科研巡检**：在Windows上由用户主动启用任务计划，复用已实现的V1.0 OpenAlex/arXiv检索和安全离线实验提案；检查五序前端官方API缓存的来源标记、结构、时间戳（36小时以内）后才读取开奖。旧版定时任务须手动停用。默认只是生成报告，不自动暂停、不自动审批、不调用付费模型、不投注。
- **可逆工程接口**：V1.4原有 `run_bridge` 和 `Registry.mask()` 在读取已暂停规则时拒绝使用，继续保持来源掩码、截止期号和SHA一致性保护。恢复操作进入同一SQLite事件哈希链。

## Windows部署

1. 下载本包、解压，在资源管理器中双击 `install_to_D_v15.bat`。安装脚本在已有 `D:\pl5` 下创建新的 `research_backend_v15` 和 `github_vendor_v15`；**拒绝覆盖已有同名目录**，保留 `frontend`、`data`、`runtime`、旧版研究后端。
2. 如果 `frontend` 不存在，安装器使用 `git` 克隆 `meilin2026dh/pl5` 并固定到已审阅的提交 `9eb9ec5ad542877680755bccf27345298ef7b99f`；若已经存在，绝不自动pull/reset/checkout。现有ESSE补丁执行受控升级，检测未经认可的修改后拒绝覆盖。
3. 运行 `启动_V15_验证.ps1`，然后分别运行 `启动_V15_科研后端.ps1`、`启动_V15_五序前端.ps1`。浏览器访问 `http://127.0.0.1:5173`。
4. 只有用户明确希望启动每6小时巡检时，才运行 `启用_V15_定时科研.ps1`。若先前登记了V1.0或V0.5任务，先人工确认并注销旧任务，以免并行重复工作。

## 算法竞争 CLI

在 `D:\pl5\research_backend_v15` 目录执行（首次需 `uv sync --python 3.12 --group dev`）：

```powershell
$DB = 'D:\pl5\runtime\algorithm_registry_v14.sqlite'
uv run python research_v15.py --db $DB status
uv run python research_v15.py --db $DB scan `
  --draws 'D:\pl5\reports\v15\official_cache_snapshot.json' `
  --source-label '已核验中国体育彩票官方历史接口缓存' `
  --report 'D:\pl5\reports\v15\competition_manual.json'
```

默认**只评估不暂停**。仅当明确希望启用自动健康暂停时，在 `scan` 添加 `--auto-pause`。该功能针对验证期出现的“**错误剔除过多**”产生警报，**不会因为删错少就将模型视为中奖概率更高**。

通过 `research_v15.py propose --text 研究文本.txt --history 仅包含截止前历史.json --source-key paper:DOI --source-ref paper:DOI` 生成受限算法候选。要求输入为 `[{"issue":"26290","date":"2026-10-31","number":"00123"}, ...]` 这样的JSON数组（举例号码仅格式演示）；程序以记录实际内容绑定SHA。随后仍需沿用V1.4 CLI审计和人工批准。

如果要从新式人工研究的官方快照生成候选规则，必须保证**资料、历史数据、公式及选择规则的确定时间在预期评价期以前**；程序只能检查期号/日期先后及快照一致性，无法证明外部操作者从未看过评价数据。

人工恢复暂停：

```powershell
uv run python research_v15.py --db $DB resume <algorithm_id> `
  --reviewer '复审人' --reason '复核数据来源、误删及后续处置说明'
```

### 工程边界

- 前端仍沿用V1.4的ESSE实验刀输入操作面板；V1.5新竞争功能通过CLI和JSON报告使用，**还没有新增React可视化规则竞争页面**。
- 当前ZIP仍只嵌入此前审阅并核验SHA的4个GitHub源模块；完整GitHub仓库由Windows安装器按固定提交获取，不能把4个文件误认成完整React源码。
- 本环境没有Windows / GitHub外网 / Docker设备；Windows Task Scheduler及完整前端的本机行为尚未验收。
- 对彩票开奖预测的零假设是公平独立均匀；保留100个不同号码的单期覆盖仍为0.1%，10期至少中一次的随机基线约0.9955%。一项稀有结构不能据此推断未来必然不出现。

## 目录

- `research_backend/pailie5/evolution_v15.py`：独立竞争与失效暂停引擎
- `research_backend/research_v15.py`：命令行操作
- `research_backend/snapshot_v15.py`：本地官方接口缓存完整性及新鲜度检查
- `research_backend/tests/test_evolution_v15.py`：规则健康、暂停/人工恢复、双引擎阻断等测试
- `research_backend/tests/test_snapshot_v15.py`：来源标签与缓存新鲜度测试
- `research_backend/定时科研_V15_运行.ps1`：人工启动的巡检执行脚本
- `启用_V15_定时科研.ps1` / `停止_V15_定时科研.ps1`：任务注册/停止

## 下一步

优先将V1.5报告嵌入React可视化面板，并把实际前向封存的待测规则和预测集合纳入一套不可回填的中心台账。前向证据以预先锁定的规则、目标期、代码版本、官方开奖结果为核心，而不是历史策略反复调参的好看回测。
