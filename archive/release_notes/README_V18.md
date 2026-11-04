# PL5 V1.8：算法能力网络（AAN）与自进化雕塑协同

**研究原型，2026-11-01。** 在V1.7原有代码基础上升级，保留官方开奖归档、科研监督、ESSE雕塑、历史验证、受审查的GitHub五序前端增量接入。

## 本版实际实现

1. **UACP 1.0算法说明书**：唯一能力ID、版本、名称、来源、输入输出类型、依赖、运算参数、执行限制、证据状态，SQLite持久化+SHA256完整性核查。
2. **算法能力网络**：DAG依赖校验、循环/缺依赖拒绝、语义重复判定、拓扑执行计划与关联图导出。
3. **受约束的能力生长**：对8种基础指标与重复、等差、交替、周期4类时序模式进行限额组合，能力增长先于准入；核心组合穷尽后按需增加新的模数、位置和位置差指标。
4. **真实执行与复现**：运行一条“历史指标→模式检测→反延续位图”任务；计算10万注全量掩码。NumPy与纯Python核对指标，保存掩码SHA256、执行路径、历史摘要和实验报告。
5. **ESSE探索型协同**：可将输出的实验位图转换为可撤销的 `Knife`，只在显式`explore`模式下使用；不自动写入正式算法准入库。
6. **五序界面能力看板**：新增只读 `/api/esse/capabilities` 与React“算法能力网络”组件，显示各算法的身份、类型、依赖、产物与研究状态。
7. **V1.7自动研究 + V1.8限额生长**：旧Supervisor成功完成论文科研后，可为能力库新增最多8条过滤候选；新任务可由Windows用户显式授权启用。

## 安装

在Windows中确保有Git、Python3.12、uv、Node.js24、pnpm11。将此ZIP解压到临时目录，运行 `install_to_D_v18.bat`。脚本将在 `D:\pl5` 使用或克隆GitHub `meilin2026dh/pl5` 前端，并安装**新的** `research_backend_v18`，保留原有全部数据和旧版代码。

如果GitHub仓库已有自定义改动，升级器将拒绝冲突操作而不是强制覆盖。新安装且原仓库不存在时，克隆官方源并固定此前审查的Git提交 `9eb9ec5ad542877680755bccf27345298ef7b99f`。部署包不包含完整GitHub仓库，已经包含之前验证的4个原版源码归档；完整源码在Windows上克隆。

然后运行 `验证_V18.ps1` 检查后端、前端类型检查、测试和构建。运行 `启动_V18_科研后端.ps1` 与 `启动_V18_五序前端.ps1`；打开 `http://127.0.0.1:5173/workbench`。能力目录会默认显示已注册能力；初次需要执行一次`bootstrap`。

### 能力网络CLI

```powershell
cd D:\pl5\research_backend_v18
$DB='D:\pl5\runtime\algorithm_abilities_v18.sqlite'
uv run python capability_cli_v18.py --db $DB bootstrap
uv run python capability_cli_v18.py --db $DB grow --limit 8
uv run python capability_cli_v18.py --db $DB graph
uv run python capability_cli_v18.py --db $DB gaps --kind anti_filter
uv run python capability_cli_v18.py --db $DB run --target pl5.metric.sum.anti_repeat_3 --history 'D:\pl5\data\official_archive_v17\official_history.csv'
```

`run`读取`number`列且不读取未来开奖，历史CSV须自行核验来源及目标截止期；程序会使用所提供的全部记录作为本期历史。实验结果**不代表真实中奖概率**。公开HTTP接口仅只读，不允许任何人通过前端自动审批、生成或执行任意Python代码。

### 显式启用长期科研

先检查并停用此前V1.7或更旧的任务，再由使用者执行 `启用_V18_定时科研.ps1`。默认每6小时调度一次；任务记录官方数据、学术情报，并增加最多8条新的**受限规则提案**。关机时不会在后台持续执行。停止任务用`停止_V18_定时科研.ps1`。

## 验收与边界

- 已实现：AAN标准说明书、确定性执行、有界公式创造、实验性ESSE合成、后端HTTP只读接口和前端增量补丁。只运行受信内置运算符，绝不直接运行论文或GitHub提供的程序。
- **尚未实现**：任意论文自动理解并忠实复现、开放式新Python算法全自动沙箱、基于本体推理的任意图谱自动规划、算法可信独立前向预测优势、无监督自动生产准入、Windows实机长期联网验收。
- **解释限制**：对公平、独立、均匀的排列五，预先确定的100注命中概率为0.1%。指标模式历史罕见不意味着下期延续更不可能。请在彩票投注前考虑经济损失风险。
