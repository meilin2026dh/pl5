> **PL5 V1.1 重要入口：** 参见 [README_V11.md](README_V11.md)。新增可逆雕塑工作台与审计评分引擎；旧版本功能保留。

> **最新版 V0.9**：请先阅读 [README_V09.md](README_V09.md)，旧版文档仍保留。

# PL5 V0.6 当前版本

请先阅读 [README_V06.md](README_V06.md) 和 [V06_技术架构与验收说明.md](V06_技术架构与验收说明.md)。原V0.5使用说明如下，相关功能仍可用。

# PL5 V0.5 自主科研与算法生长智能体

请优先阅读 [README_V05.md](README_V05.md)，V0.4原有功能完整保留。

# 排列五 · 多智能体算法发现与严格验证系统 V0.2

> **研究软件，不是彩票预测器，不自动投注。** 在公平、独立、均匀开奖条件下，每期持有 K 个不同号码，单期准确命中的概率为 K / 100,000。模型复杂度和历史回测不能改变这一基线。

## 版本说明

本目录是 **V0.2的独立项目副本**，保留了 V0.1 的 `app.py`、`cli.py`、`pailie5/engine.py`、`pailie5/backtest.py` 等实现，新增第二阶段核心能力：

- `phase2_app.py`：阶段二网页工作台（数据入库、自动研究、预注册、知识库审计）。
- `agent_cli.py`：新命令行入口，`import` / `fetch-community` / `sources` / `experiments` / `research`。
- `pailie5/knowledge.py`：SQLite来源登记、SHA-256文件指纹、冲突阻断、五位/七位期号归一化、一次性封存测试集锁。
- `pailie5/sources.py`：**可选第三方数据镜像**固定URL适配器。仅在明确调用时联网，社区来源**不是官方认证数据**。
- `pailie5/discovery.py`：受限DSL算法描述、位置/联合/时间衰减假设、可复现DSL组合生成、可选LLM的有限JSON提案。
- `pailie5/research_agent.py`：六节点研究工作流与LangGraph/SQLite checkpoint可选集成；预注册再读取测试集。
- `tests/test_phase2.py`：包括未来数据泄漏、来源一致性、重复开封和DSL不执行任意代码等自动测试。

**已在当前运行环境验证**：全项目 `pytest -q` 的17项测试通过；使用伪随机演示数据完成一次端到端研究；第二次试图打开同一测试集会被阻断。未在当前环境安装Streamlit或LangGraph，故UI启动及实际LangGraph运行仍需在本机依照下列步骤验收。

## Mac安装与启动

Python 3.12 + `uv`，避免修改系统Python：

```bash
# 如果没有uv，请先安装，参见 https://docs.astral.sh/uv/getting-started/installation/
cd pailie5-agent-v02
uv python install 3.12
uv sync --python 3.12 --extra agent --group dev
uv run pytest -q
uv run streamlit run phase2_app.py
```

浏览器访问终端显示的地址（通常是 `http://localhost:8501`）。项目仅在自己的 `.venv` 下运行，不配置API Key也可使用大多数功能。

如需启用语言模型**仅生成受限实验参数**，可另行安装：

```bash
uv sync --python 3.12 --extra agent --extra llm --group dev
export OPENAI_API_KEY='你自己的API密钥'  # 仅本机交互输入；勿写进项目文件
uv run python agent_cli.py research --llm --graph required
```

调用外部大模型会产生第三方API调用及可能的费用。**本项目绝不执行大模型生成的Python代码**，只接受通过白名单验证的JSON模型参数；未设置密钥时退回确定性实验。`--llm` 无效或不可用也会安全回退。

## 第一次研究：使用演示数据

演示数据是伪随机产生的，不是任何一期真实开奖：

```bash
uv run python agent_cli.py --db runtime/demo_trial.sqlite research \
  --demo --graph auto --count 1000 --dev-size 40 \
  --holdout-size 40 --min-train 100 \
  --output runtime/demo_report.json
```

会先从候选假设中选模型，再预注册，然后只打开一次末尾40期的封存测试集；会生成JSON报告。假如全部算法未达到开发集统计门槛，会**自动选择随机对照**，而不是强行输出所谓的“高概率号码”。

**同一演示数据库、同一数据、同一封存窗口，第二次执行会被拒绝**。这是有意设计。若要尝试另一个模拟研究，请使用新的专用数据库文件；同一真实测试集不能靠换参数反复开封。

## 接入真实开奖记录：两种方式

### A. 推荐：手动核验后导入官方记录整理的CSV

官方参考入口：
- 中国体彩网排列5历史开奖页：https://m.lottery.gov.cn/zst/plw/
- 福建省体彩网排列5历史开奖页：https://www.fjtc.com.cn/node_309522.htm?gameType=plw
- 甘肃省体彩网排列5历史记录：https://www.gstc.org.cn/wanfa/pl5_history

CSV仅需两列，**保持开奖号码为精确5位**，避免Excel自动丢失前导零：

```csv
period,number
2026270,64124
2026271,62246
```

**上面仅为CSV格式示例，不能当作未核验的真实数据库内容使用。** 实际数据请在官方公告中逐期核对。

```bash
uv run python agent_cli.py import --csv /实际路径/pl5_history.csv --source '官方网页人工核对：来源链接+日期'
uv run python agent_cli.py sources
uv run python agent_cli.py research --graph required --count 1000 \
  --dev-size 100 --holdout-size 100 --min-train 500 \
  --output runtime/official_study.json
```

入库时：
1. 严格要求五位数字，不能通过悄悄补零修补错误；
2. `YYNNN`（如`26271`）与`YYYYNNN`（如`2026271`）统一为七位；
3. 所有已登记来源与入库数据会比对；同一期号不同号码时**整批拒绝、绝不覆盖**；
4. 为每份源文件记录SHA-256、来源名称、行数、时间戳；
5. 无法自动证明某CSV确实来自官方，请保存原始公告或完整原始文件。

### B. 可选：从第三方公开镜像获取历史CSV

如用户同意通过联网方式获取第三方数据，可执行：

```bash
uv run python agent_cli.py fetch-community
```

固定来源：`https://raw.githubusercontent.com/BrookeMa/pl5-data/main/pl5_5digit.csv`，上游社区项目声称来自 `data.17500.cn`。它**不是中国体彩网或各省体彩网的官方数据源**，下载后仍需抽查近期/早期公告并与官方数据交叉比对。该命令需要本机网络；当前制作环境无外网DNS，因此**没有执行成功的真实在线抓取实例**。镜像字段固定适配 `period,date,winningNumber`，会执行记录数/排序/重复期号/5位号码校验。

离线下载后，也可运行：

```bash
uv run python agent_cli.py fetch-community --file /路径/pl5_5digit.csv
```

## V0.2的六节点工作流

```text
validate（数据验证、查重、确认封存未开封）
   ↓
propose（本地模板 + DSL程序合成 + 可选LLM JSON参数）
   ↓
develop（只看开发集，滚动评价7个以内的算法）
   ↓
preregister（将模型、目标K、窗口和划分写库并锁定）
   ↓
open_holdout（第一次读取封存集，计算独立检验）
   ↓
audit（生成报告、保存算法证据和状态）
```

`--graph auto`：如果安装了LangGraph和SQLite checkpoint扩展，就用真实StateGraph/检查点执行，否则使用相同节点的顺序执行。`--graph required`：强制图运行，未安装即报错，不虚称使用了LangGraph。`--graph off`：纯离线，不依赖LangGraph。

`--llm`是可选研究辅助模块，**不是联网的自主写代码执行器**；即便安装了LangGraph也不代表接入了语言模型。

## 模型淘汰规则

- 模型候选集：位置频率、二位置联合、融合、时间衰减、2项通过DSL自动生成的混合模型；若启用LLM可以产生有限数量的受限参数变体。
- 每个测试期 `t` 仅利用 `t` 以前的数据估计分布；不会用 `t` 自身号码参与评分。
- 开发集指标：对实际开奖结果的**归一化log概率**与完全均匀分布的差值（不是原始未校准分数）；模型跨开发期log增益必须经多重比较校正后达到门槛，才有资格进入封存集。
- 所有开发模型无证据时，退回均匀随机基线。
- 通过开发集门槛的唯一冻结模型，才在一次性封存集上检查命中期数、均匀基线期望、二项检验及平均log增益。
- 命中期数在小K情况下会十分稀少，少量命中不能证明可重复预测性；无论结果如何，仍需要未来新增开奖进行独立复现。

## 风险、限制与待实现

- V0.2不具备实时官方API的已验证自动接入；第三方镜像属于**可用性未知的选装连接器**。
- 统计选模使用正态近似与Bonferroni校正，有限样本、时序相关和研究者重复试验仍可能导致不可靠结论；不是因果偏差证明。
- SQLite封存可以阻止本软件对同一数据库的重复开封，不是防篡改的公证系统；复制数据、换数据库或重新研究仍可以绕过本地管控，需要审计纪律。
- 目前仅有受限DSL“自动合成评分模型”，未实现LLM自主编写/执行全新Python算法。后续如需该能力，必须有容器沙箱、权限隔离、资源上限、代码审查与独立验证。
- 没有任何自动投注、收款、下注调用、承诺中奖率的模块。

详细设计请看《技术实施方案.md》。

## 双击启动脚本

- Mac：`启动_Mac.command`（系统可能要求右键 → 打开）。
- Windows：在PowerShell中运行 `powershell -ExecutionPolicy Bypass -File .\启动_Windows.ps1`。

脚本检测 `uv`、使用Python 3.12建立本项目的专用虚拟环境、安装选装图框架并启动第二阶段Web工作台。首次安装依赖需要互联网；不自动安装系统级uv、不覆盖系统Python、不配置API Key。

## V0.3 新增：指标时序反延续 + 跨空间映射研究

- `pattern_app.py` 与 `rank_app.py`：历史N期模式识别、用户选择规则、10万号码实验性排序（概率并未经过实际中奖率校准）。
- `pailie5/space_mapping.py`：23选6、41选4及11位310空间的可逆映射、组合/三态指标、跨期指标。
- `pages/03_跨空间映射实验室.py`：跨空间编号查看、指标选择、模式检测、手动规则选择、全量排名与CSV导出。
- `跨空间映射过滤_设计说明.md`：数学定义、技术接口、统计基线和验证边界。

三种空间均保留原始排列五的完整10万注编号，默认展示可逆置换映射。**映射并不会增加彩票的可预测信息**。第一轮集成测试50项通过；GUI和Windows实际部署尚待本机验收。

---

## V0.4：三项新增能力

**新页面**：`pages/04_多空间竞争与稳健性.py`，用原有Streamlit入口 `uv run streamlit run phase2_app.py` 打开后在左侧菜单选择。

1. 四空间同时配置指标、变换、时序模式、历史窗口，完整输出10万候选排序；支持原有基本规则。
2. 规则竞争：原始覆盖、边际覆盖、冗余率、空间Jaccard/Phi相关、分规则和分空间的逐期滚动回测；与条件随机基线逐期对照。
3. 映射安慰剂：正式映射及一组预固定单射映射，同样的历史窗口与期号，检验Top-K、对数损失、剔除集合重合度；无信号时明确报告信息不足。

`pailie5/multispace.py`：`multi_space_study`、`competition_backtest`。

`pailie5/mapping_robustness.py`：`robustness_study`、`fixed_variants`。

`multispace_cli.py`：离线运行且可导出全部10万号码和回测JSON：

```bash
uv run python multispace_cli.py --csv data/synthetic_demo.csv --demo --out runtime/v04_demo
```

完整机制、数学边界、安全升级与验收清单参见 **`PL5_V0.4_三项新增能力与验收说明.md`**。在Windows上使用升级包根目录的 `install_to_D_v04.bat`，将修改合并到 `D:\pl5` 前会备份将覆盖的旧程序文件，同时保留数据及运行环境。

## 最新版本（V0.8）

请先阅读 [README_V08.md](README_V08.md) 和 [V08_设计与验收报告.md](V08_设计与验收报告.md)。
开放Python科研实验页为 `pages/08_开放Python算法科研实验室.py`，命令行入口为 `research_v08.py`。


## V2.9 有限域基础数学算子发明

新增`research_v29.py`与`pages/17_基础数学算子发明实验室.py`，可自动学习新100格二元数学运算表，并绑定训练历史数据指纹，在AAN和BCSE研究层使用。详情见`README_V29.md`。
