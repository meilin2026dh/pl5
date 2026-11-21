# PL5 V2.6 · 高维隐结构发现与自主表示学习（HDSE）

这是对 V2.5 的**增量升级**，保留原有基础过滤、23选6映射、九空间、时序反延续、ESSE雕塑、AAN能力说明书、自主科研调度等模块。它不直接证明彩票开奖可以预测。

## 本次实现

| 算法家族 | 真正计算的表示 | 上限与限制 |
|---|---|---|
| 高阶稀疏张量 | 5位置一阶、10对位置二阶、10组三位置三阶离散交互 | 一共50+1000+10000=**11050坐标**；按组合分组边缘频数平滑，不分配100000×11050矩阵，不是任意高阶因果模型 |
| 时空联合状态 | 当前数字、前1期及前2期的条件数字状态 | 二滞后最多5×(10+100+1000)=**5550个状态参数槽位**，历史不足通过层级平滑回退；使用当期之前已知的开奖上下文 |
| 有限群傅里叶谱 | 在Z₁₀⁵上构造1—3阶的离散傅里叶角色 | 频率空间45+810+7290=**8145个候选非零字符**；选择最多32个共轭约简后的谱峰，必须与均匀随机噪声对照 |

**模型选择**：训练段拟合参数，开发验证段同时选择表示和均匀混合λ∈{0,.1,.25,.5,1}，冻结后在历史留出段只检验一次。如果开发验证不优于均匀，自动退回均匀实验基线。

**辅助科研**：给出训练段位置对残差的奇异值诊断（不是因果）、谱峰及样本量/高维坐标比；可以重新在完全独立的IID随机序列上运行整个选择流程检测虚假发现倾向。

**算法网络增长**：`cycle`把三种家族下的不同有意义参数配置注册进SQLite。当前是**44种有界配置**，不是无穷的新算法；重名或不影响输出的伪参数不重复登记。该过程只增长工程研究库，不触碰正式预测规则。

## Windows D盘安装

1. 解压完整包，双击 `install_to_D_v26.bat`。新后端将位于 `D:\pl5\research_backend_v26`；如已存在则拒绝覆盖。
2. 执行 `验证_V26.ps1`，检查新旧专项测试。
3. 执行 `启动_V26_高维实验室.ps1`，打开浏览器研究页面。
4. 如需单独每6小时登记一批高维能力提案，可显式执行 `启用_V26_定时表示研究.ps1`；应先核查旧V2.5/V2.2任务以免叠加消耗。未授权不会自行注册后台任务。

历史数据保存在原 `D:\pl5\data`，旧版本和历史数据库都不删除。当前安装包并未包含GitHub React完整仓库；新增高维功能先通过Streamlit页面、CLI及HTTP桥接开放。

## CLI命令

在`D:\pl5\research_backend_v26`执行：

```powershell
uv sync --python 3.12 --group dev
uv run python research_v26.py capabilities
uv run python research_v26.py propose --maximum 12 --seed 20261102 --report reports/v26_proposals.json
uv run python research_v26.py cycle --db D:\pl5\runtime\hdse_v26.sqlite --maximum 12
uv run python research_v26.py status --db D:\pl5\runtime\hdse_v26.sqlite
uv run python research_v26.py study --history D:\pl5\data\official_history.csv --maximum 7 --test-periods 40 --budget 100 --null-trials 3 --report reports/v26_official.json --numbers reports/v26_candidates.csv
uv run streamlit run "pages/14_高维隐结构发现实验室.py"
```

不含官方数据时可用 `demo` 启动独立同分布均匀**合成数据**实验；绝不能将其称为实测预测效果。

## HTTP接口

- `GET /api/esse/hdse-v26/capabilities`：能力说明书。
- `GET /api/esse/hdse-v26/registry`：只读研究能力登记状态。
- `POST /api/esse/hdse-v26/research`：不提供history时只生成研究提案；提供 `history` 五位数字数组时，按 `maximum`、`budget`、`test_periods`、`seed`、`null_trials` 运行时间外研究。接口历史≤2000期、随机对照≤2次、请求体限制700KB，服务仅绑定127.0.0.1。

## 数学边界

若各期开奖独立、均匀，下一期号码X与过去H独立，则I(X;Φ(H))=0。高维表示有助于**表达原本存在的复杂结构**，不会产生新的预测信息。公平开奖下，K注命中概率严格为K/100000，100注对应0.1%，连续10期至少命中一次约0.9955%。

无足够前向证据之前，程序里的“模型概率”属于研究性概率分布，不是校准过的单注中奖概率。研究选模可在大量特征中挑出随机峰，单次历史留出乃至几期表现变好都不是突破证明。

可选导出全10万注的实验性排名，在上述`study`命令后追加 `--full-ranking reports/v26_all_100000.csv`，四列包括排名、五位号码、研究性模型分数和均匀基线。只有数学实验用途，不得误称真实中奖概率。
