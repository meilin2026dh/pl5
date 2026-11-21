# PL5 V2.7 · BCSE 贝叶斯软约束雕塑引擎

本版本基于 **V2.6 HDSE 原始完整项目**增量开发，继续保留基础过滤、历史时序反延续、23选6及九空间映射、高维表示、AAN能力网络和ESSE规则雕塑。新增加一个**有限模型贝叶斯软约束科研子系统**，不是实际彩票中奖概率的保证。

## 核心能力

- 统一计算全100000个五位有序号码的约束违反掩码（保留前导零）。当前6个算法能力：邻位绝对步长超阈值、没有0路数字、全奇/全偶、最近3期和值尾重复延续、最近3期和值非零等差延续、位置数字三期重复延续。
- 可在UI和JSON中选择1—8条规则（允许不同阈值的步长规则），自动按完整位图检测近重复，避免把高度相关规则简单视为独立证据。
- 在**60期前缀**上拟合位置数字Dirichlet平滑先验分布，之后在不使用未来开奖的情况下计算多个有限软约束模型的贝叶斯后验权重；包括固定的均匀零模型、位置Dirichlet模型、单规则及两规则组合模型。
- 规则惩罚系数使用事先固定的离散研究网格（-0.8、0.6、1.4及部分成对0.6）；负系数可表达“数据偏向违反规则”，不能预设所有反延续假设成立。
- 使用训练期更新模型权重，独立开发验证阶段决定是否启用非均匀模型，最终留出阶段**只进行一次评价**。验证不通过就回退均匀概率，并采用事先固定随机种子为完全并列号码排序。
- 对每注输出**模型后验平均分配概率、95%模型条件可信区间、后验平均有符号违例惩罚、惩罚区间和被模型抑制的后验质量**。完整10万注可导出CSV。
- 候选数1—100，提供同预算随机对照和IID均匀模拟全流程压力测试。含研究报告历史SHA256、模型后验和分段统计。
- 本版可直接作为研究能力加入AAN，但**不会自动晋升为正式预测算法**。

## Windows部署

从ZIP解压后双击 `install_to_D_v27.bat`，将完整源码独立安装到 `D:\pl5\research_backend_v27`（如果目录已经存在就拒绝覆盖）。原 `data`、`runtime`、旧后端和GitHub前端不删除。

运行 `验证_V27.ps1` 完成依赖安装和专项测试，之后运行 `启动_V27_贝叶斯实验室.ps1`。本机须先安装Python 3.12、uv。默认网页是Streamlit研究页面，完整GitHub React前端未包含在该ZIP中，现有五序前端仍可通过本机HTTP接口与研究后端通信。

## CLI

在 `D:\pl5\research_backend_v27` 中执行：

```powershell
uv sync --python 3.12 --group dev
uv run python research_v27.py capabilities --report reports/v27_capabilities.json
uv run python research_v27.py demo --budget 100 --test-periods 30 --report reports/v27_iid_demo.json --candidates reports/v27_demo_numbers.csv
uv run python research_v27.py study --history D:\pl5\data\official_history.csv --validation-periods 35 --test-periods 30 --budget 100 --null-trials 1 --report reports/v27_official.json --candidates reports/v27_official_top100.csv
uv run python research_v27.py study --history D:\pl5\data\official_history.csv --budget 100 --report reports/v27_all_report.json --full-ranking reports/v27_all_100000.csv
uv run streamlit run "pages/15_贝叶斯软约束科研实验室.py"
```

请先确认`official_history.csv`确实由官方渠道取得且期号、日期无缺漏或冲突。要求包含`number`列，建议`issue,date,number`。CLI会校验号码格式及重复期号；**它不自动保证用户所上传的CSV确实来源于官方**。

自定义约束配置：

```json
[
  {"id":"step8","kind":"step_large","threshold":8},
  {"id":"tail","kind":"sum_tail_repeat"},
  {"id":"parity","kind":"parity_extreme"}
]
```

保存为JSON，运行时增加 `--constraints 文件.json`。

## HTTP本机接口

- `GET /api/esse/bcse-v27/capabilities`: UACP能力说明书；
- `POST /api/esse/bcse-v27/research`: 含`history`数组（150—2000条）、可选`constraints`、`budget`、`validation_periods`、`test_periods`、`dirichlet_alpha`、`seed`、`null_trials`的研究请求。
- 不提供`history`时只返回研究能力清单；本机API返回摘要和最多30注明细，不在HTTP中传输完整10万行以免阻塞。全量CSV走CLI或页面导出。
- HTTP默认服务仅绑定`127.0.0.1`，启动命令 `uv run python integration_server.py`。

## 重要数学边界

模型为 **\(P_m(x|H_t)=q_m(x)\exp[-\sum_j\lambda_{mj}v_j(x,H_t)]/Z_m(H_t)\)**，其中`q_m`是均匀或60期前缀拟合的Dirichlet位置分布；`Z_m`在全部10万注上精确计算。模型后验采用固定离散模型先验与训练段的逐期对数似然累积，而不是假设各规则产生独立证据再相乘。

“违反规则”是确定性0/1事件；有不确定性的是**这条规则是否有统计预测价值及其软惩罚权重**。95%区间只在选定模型族和先验条件下有后验解释；不能直接当作频率学置信区间、开奖设备的真实分布或保证命中范围。模型的全部评分都可能优于或劣于均匀，但只有足够的独立前向检验才有证据意义。

公平独立开奖下，固定或过去历史自适应选出的K个不同号码，其下一期精确覆盖率总是`K/100000`，100注为0.1%。
