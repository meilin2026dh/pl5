# PL5 V0.9 — 自主科研：论文复现证据链与统计证伪门禁

**增量升级，保留V0.1—V0.8已有基础过滤、时序反延续、跨空间、文献发现、自主生成代码、Docker隔离回测与前向登记。**

> **核心边界**：PL5是研究系统，不能保证中奖。公平独立开奖下，固定100注/期单期精确命中概率=0.1%；10期至少一次约0.9955%。生成再多过滤规则也不能凭“规律罕见”提升公平开奖的条件概率。

## V0.9三个模块

### 1. 论文—实现—数据来源证据链 (`autoresearch/replication_v09.py`)

- 每个论文启发的算法必须登记研究协议：文献标识、公式/页码定位、前提条件、实现步骤、数值参考样例、V0.8代码SHA256。
- 区分 `method_adaptation`（新方法迁移）与 `claimed_author_reproduction`（论文原方法复现声明）。声明本身**不构成**复现成功。
- 对三种内置数值特征（五位和值、奇数个数、相邻位置变化次数），使用纯Python循环与NumPy数组算术**两份独立编写的可信实现**，遍历100000个号码交叉验证。该测试只能证明**这三个基础特征的实现一致**，不能证明任意论文或V0.8候选评分代码已被复现。
- 登记协议后不可静默编辑；内容用SHA256校验。研究复现报告另行保存，任何报告的 `faithful_paper_reproduced` 默认为false。

### 2. 开放Python代码配对审查 (`autoresearch/pair_review_v09.py`)

- 人工提交第二份不同SHA256的实现、出处及两者独立开发的依据。
- 在明确 `--allow-docker` 后，两个实现各进行两次**独立Docker进程**运行，检查同一批历史窗口、10万注Top-K排名是否一致。
- 任一实现两次输出不一致、或两份代码排名不同，配对验收不通过。
- **目前比较的是Top-K排名而非每注的完整浮点评分**。两份代码不同亦不能证明独立开发或数学等价。没有Docker时不会执行外部生成代码，拒绝退回宿主机运行。

### 3. 预注册多模型证据账本 (`autoresearch/evidence_v09.py`)

- 算法作为一个新的研究系列注册；必须链接到已有V0.8代码及V0.9研究协议。
- 新系列按不可修改的顺序领取一个错误预算：第i个系列 `α_i=0.05/[i(i+1)]`，所有系列累计不超过5%。每个系列按照*开奖前确定的*100注以内候选集合构造预先固定的4种Bernoulli似然比混合e-process。
- 每次候选集提交后哈希封存，开奖结果入账后不能改变；早期未结算时停止发布后续证据，防止选报中奖期。
- 通过Ville不等式和并集界：**只有在公平独立开奖、真正开奖前固定候选集、结算完整等条件都成立时**，这套预先固定的检验门槛才有控制整个注册模型家族假阳性的数学含义。
- 不将任何研究结果自动投入正式选号/投注。输出 `predictive_edge_proven=false`；即使穿越证据门槛，也不能保证未来10期中奖。
- **真实缺口**：本机SQLite时间戳与SHA256不足以独立证明当时未知开奖；官方公告来源目前依赖人工核验，未与第三方可信时间证明集成；用户手动提交候选列表与登记代码的一致性还未自动逐行证明。因而正式预测优势仍不可宣称。

## 安装：Windows D盘

1. 下载完整版ZIP并解压到本机任意目录（应见 `pl5` 子目录）。
2. 双击根目录 `install_to_D_v09.bat`，将程序合并安装到 `D:\pl5`。覆盖的旧程序会先备份；`data`、`runtime`、`.venv`、`archive`、`research_reports` 不会被覆盖。
3. 在PowerShell执行：

```powershell
cd D:\pl5
uv sync --python 3.12 --extra agent --extra fulltext --group dev
uv run pytest -q
uv run python research_v09.py demo
uv run python research_v09.py check-kernel --method digit_sum
uv run streamlit run phase2_app.py
```

新页面：`09 独立复现与证据门禁`。

### CLI命令

```powershell
uv run python research_v09.py demo
uv run python research_v09.py status
uv run python research_v09.py check-kernel --method transition_count
uv run python research_v09.py protocol-create --json examples\v09_protocol_template.json
uv run python research_v09.py protocol-list
uv run python research_v09.py protocol-check --protocol-id <协议SHA256>
uv run python research_v09.py pair-register --protocol-id <协议ID> --primary-id <主代码SHA> --reference-id <独立代码SHA> --reviewer reviewer --independence-basis "人工核对两套实现由不同人员或独立思路设计，未共用核心实现逻辑。"
uv run python research_v09.py pair-audit --pair-id <配对ID> --csv data\official_history.csv --k 100 --eval-size 8 --allow-docker
uv run python research_v09.py register --model-id algo_001 --code-id <代码SHA256> --protocol-id <协议SHA256> --reviewer reviewer
uv run python research_v09.py seal --model-id algo_001 --period 2026999 --previous 2026998 --candidates candidates.txt --history-sha256 <64位摘要> --source "official:人工核验公告"
uv run python research_v09.py settle --period 2026999 --number 01234 --data-sha256 <64位摘要> --source "official:人工核验公告"
uv run python research_v09.py report
```

上述期号和号码都是**格式示例，绝非真实期开奖、实盘推荐或已存在的期号**。`v09_protocol_template.json` 的代码ID为占位符，使用前必须更换为V0.8实际登记的代码ID，并登记原始文献。不要将示例记录写入真实运行数据库。

`demo` 仅使用内存SQLite和伪随机号码，不会污染正式数据库；它会生成 `examples/v09_synthetic_evidence_demo.json`。

## 审核顺序与准入标准

| 等级 | 允许 | 不允许 |
|---|---|---|
| L0 文献线索 | 加入研究库，摘取数学定义与风险 | 声称论文可预测彩票 |
| L1 研究协议 | 保存作者方法、数据假设和参考输出 | 将论文启发算法包装为忠实复现 |
| L2 工程审查 | 静态检查、独立实现交叉核验、Docker沙箱 | 将两次相同代码运行当独立复现 |
| L3 统计验证 | 预登记模型与错误预算，封存每期候选集 | 多个算法反复复用同一期而不调整门槛 |
| L4 研究发布 | 保存实验、拒绝、失败与研究结论 | 自动发售/投注/宣布10期必胜 |

## 当前真实验收边界

- 新模块单元测试、旧版回归测试可在当前环境执行；真正Windows页面、Docker联机/容器沙箱仍需在目标机验证。
- 使用V0.9内置方法核验不需要Docker；开放Python实现配对**需要**Docker；如果Docker不可用，配对审查将拒绝执行。
- 官方开奖同步由V0.1—V0.8原有渠道负责；V0.9不会自行假造历史开奖号或替用户声称已核验。
- 定时科研任务继续采集论文与提出算法。V0.9仅增加一个**只读统计台账状态输出**，不会定时运行未知代码、封存候选或自动批准新模型。

## 相关统计依据

- Xu & Ramdas, *Online multiple testing with e-values*, AISTATS 2024: https://proceedings.mlr.press/v238/xu24a.html
- Grünwald et al., *Safe testing*, JRSSB 2024: https://doi.org/10.1093/jrsssb/qkae011
- NIST SP 800-22, 随机性统计测试不能绝对证明随机生成器可靠：https://csrc.nist.gov/pubs/sp/800/22/r1/upd1/final

**注意**：我们采用的是易审计的固定预算分配与混合似然比，不声称完整实现上述论文中的e-LOND或复杂在线FDR算法。
