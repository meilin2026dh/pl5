# PL5 V0.6 — 自主算法创造、复现与证伪智能体

**工程定位：** 在V0.5现有基础过滤、时序反延续、跨空间映射、规则竞争、自主论文巡检之上，新增完整的受限科研实验流水线。

> **绝不保证预测彩票。** 对公平独立的排列五开奖，100注/期命中概率为0.1%，10期中至少一次约0.9955%；复杂公式、稀有模式及历史最佳回测都不能改变数学基线。排名为实验偏好，不是经过验证的中奖概率。

## 本版实现了什么

1. **论文全文接入**：可导入本地PDF、TXT、MD；可按严格验证的现代arXiv编号访问arXiv PDF。PDF 8MB、最多24页及7万字符；不允许任意网络URL、跳转或从开源仓库自动执行代码。API离线无法验证时请用本地文献。
2. **自主公式发明**：文献主题驱动的可复现文法搜索，构造2~3层数学表达式AST，支持14种基础指标、7种安全运算、5种时序模式；可选、**必须显式授权且产生费用**的大模型JSON提案。
3. **源代码审阅**：为算法生成供人审查的Python表达式源码；**不会执行、导入或安装模型或论文生成的代码**。真正运算来自受约束的AST解释器。
4. **独立数值复现**：同一表达式分别通过NumPy向量引擎和不依赖指标向量表的纯Python逐号码计算，抽样交叉验证；候选集合重新生成并检查哈希一致性。
5. **自动证伪**：严格按期回测；每期候选在开奖前可知的历史中产生；同时生成新IID公平开奖序列并运行零假设对照；记录原始/探索性Bonferroni校正p值、触发次数、命中数和数据哈希。
6. **证据库与准入**：SQLite保存文献、算法公式、开发回测和审计。对同一数据集指纹/算法跳过自动重复实验。只有带审计ID和明确操作员声明的人工批准才能进入**研究算法库**；不自动激活原有正式过滤器。
7. **研究库独立Top-100**：可选使用人工批准的公式输出研究性最多100注、导出CSV并借用V0.5现有开奖前本地封存逻辑；不认可这些公式具有中奖优势。
8. **定期科研巡检**：原V0.5每6小时Windows定时脚本，追加V0.6新文献入库→算法创造→实验；如果启用官方历史CSV及来源说明，才开展开发集回测。**Windows定时任务需要用户在本机手动启用**。

## Windows安装/升级到D:\pl5

1. 下载ZIP并在临时目录解压，文件夹结构为 `pl5\` 和 `install_to_D_v06.bat`。
2. 双击 `install_to_D_v06.bat`。它仅允许操作 `D:\pl5`，复制之前备份已有程序，**保留** `data`、`runtime`、`research_reports`、`.venv`、`archive`，对已存在的 `config` 也予以保留。
3. PowerShell中运行：

```powershell
cd D:\pl5
uv python install 3.12
uv sync --python 3.12 --extra agent --extra fulltext --group dev
uv run pytest -q
uv run streamlit run phase2_app.py
```

浏览器左侧选择“**06 算法创造复现与证伪**”；原来的05页面以及基础/多空间页面仍保留。无uv环境需要自行预先安装uv；脚本不修改系统Python。

### 常用命令

```powershell
cd D:\pl5
# 1. 先巡检科研信息（现有V0.5功能）
uv run python research_cli.py scan

# 2. 将已有论文摘要作为研究线索导入V0.6
uv run python research_v06.py ingest-leads --max-documents 5

# 3. 可选：由arXiv论文编号获取全文（需要联网和fulltext依赖）
uv run python research_v06.py fetch-arxiv --arxiv-id 2501.01234
# 上行ID只是格式示例，不代表推荐该论文。

# 或使用人工下载的论文全文；无需网络
uv run python research_v06.py import --file research_papers\paper.pdf --key my-paper-01 --title "我的研究论文"

# 4. 从已有研究文本自主生成复合指标和候选算法（完全离线、无API费用）
uv run python research_v06.py invent --key my-paper-01 --limit 6

# 5. 只有显式选择该选项才调用付费大模型提案API（需配置OPENAI_API_KEY）
uv run python research_v06.py invent --key my-paper-01 --paid-llm

# 6. 对单个算法做复现与证伪
uv run python research_v06.py experiment --fingerprint <算法指纹> --csv data\official_pl5.csv --official-source "official:已经核对中国体彩官方开奖" --eval-size 120 --null-sequences 6 --k 100

# 7. 批量研究：无历史CSV时仅自动创制新公式，不做回测
uv run python research_v06.py cycle --max-documents 3 --algorithms-per-document 2

# 8. 如果要明确启用研究算法库，请人工审查某次审计报告后再登记（不是通过预测验证）
uv run python research_v06.py approve-research --fingerprint <算法指纹> --audit-id <审计ID> --reviewer "操作员" --consent I_APPROVE_RESEARCH_ONLY

# 9. 独立研究性排序（已审批的研究公式才参与）；不更改旧排名程序
uv run python research_v06.py rank-approved --csv data\official_pl5.csv --official-source "official:已经核对中国体彩官方开奖" --k 100
```

将上文`<...>`替换为实际指纹/ID；源码不会自行核实“官方来源声明”是否真实，使用者仍需逐项核对公告。

### 真正开启定时科研

```powershell
cd D:\pl5
powershell -ExecutionPolicy Bypass -File .\启用_定时科研.ps1
# 如果要每轮自动进行官方历史CSV回测，可在启用时明确设置：
# powershell -ExecutionPolicy Bypass -File .\启用_定时科研.ps1 -OfficialCsv 'D:\pl5\data\official_pl5.csv' -OfficialSource 'official:已逐期核对中国体彩公告'
# 停用
powershell -ExecutionPolicy Bypass -File .\停止_定时科研.ps1
```

任务由Windows计划任务驱动，电脑关机就无法运行；本次仅交付程序，不代表已经在你的D盘安装或建立任务。不自动购买彩票。不自动运行付费LLM提案；要自动付费调用需另行明确配置专门的付费任务。

## 研发边界与科学审计

- **“复现”有两个含义。** V0.6已经实现的是*自动构造的新公式在两套计算器上的工程复现*，以及同样实验可重跑的复现；不等于完整复现任何任意数学论文的实验/结论。论文真正的原始实验复现仍需专门适配。
- **“创造”有范围。** V0.6是安全的公式树组合与可选模型提案，不是可以自行安装库、修改主程序的无限制代码生成智能体。外部原始文本不具有执行权限。
- **“证伪”有范围。** 这里是开发集逐期验证、随机公平对照和代码复现，不可能穷尽证明一个统计规律不存在。开发集显著性在大量试验下容易是噪声；真正的性能结论必须预先冻结算法并积累未来样本。
- **统计提示。** 每个固定K候选集单期公平开奖命中率是K/100000；对随机号码来说，模式延续仍是可能的。即使抽样观察到一定规律，也必须先排查数据质量、重复试验、错误的独立性假设。
- **审计局限。** 审计表和本地预注册由本机管理，不是不可篡改的独立时间证明。对于严肃的前向实验须做第三方时间戳、永久冻结和完整失败实验登记。

## 本地验收结果（当前执行环境）

- **83项pytest自动化测试通过**，包含V0.1–V0.5全部原有模块的回归测试以及新增V0.6测试。
- 通过1000期**合成演示数据**完成3条自主表达式算法的文献→发明→审计实验流程；60期开发回测中三条各0命中，符合极稀少命中事件的直观预期，不能证明预测能力。
- 本次联网arXiv PDF抓取、真实OpenAI模型调用、Windows平台的任务计划程序以及Windows GUI启动均**尚未实际联机验收**。

> 科研自主运行依赖本地定时任务和正常运行的Windows电脑；聊天本身不会在对话结束后替你持续运行科研程序。

定时研究需要每期更新已核对的CSV；本版本不会自动从非官方镜像抓取开奖号码。若未在定时任务中配置官方CSV，默认只做文献发现和公式生成，不开展历史回测。
