# PL5 V2.4 · 九空间特征与协同过滤实验版

## 本次真正实现了什么

在既有V2.2科研后端上新增 `pailie5/nine_spaces_v24.py`、`research_v24.py`、Streamlit实验页 `pages/12_九空间协同过滤实验室.py`，保留老代码。该模块是**探索性计算系统，不是经过验证的中奖预测系统**。

| 空间 | 可用指标 | 条件及边界 |
|---|---|---|
| 属性十五位 | 奇数、大数、数学质数个数、型码签名、型码种数 | 只有7种单位置型码，0和1不属于数学质数 |
| 和值/跨度 | 和值、和尾、跨度、和值桶、尾跨度联合状态 | 和尾由和值决定；联合类别不能当成独立证据 |
| 012路 | 243种路型、0路数量、同路、切换次数、逐位置转移评分 | 每种路型含的原始号码数不同 |
| 步长空间 | 四个绝对差、带符号差、总差、最大差、零差与大差数 | 绝对差丢掉方向，首位+符号差才可无损恢复 |
| 对称位对 | 两端和/差各两组、中位、联合签名 | 对称和差不能区分每对数字的顺序，**不是**一一变换 |
| 热度50维 | 逐位置历史频率、候选负对数频率、3主成分重构残差 | 至少30期；PCA重构异常非开奖概率 |
| 二阶马尔可夫 | 上两期条件下的逐位置平滑转移对数评分、支持次数 | 极稀疏，需历史前缀拟合，不将“未见过”设为零概率 |
| 组合映射 | 23选6的可逆编码、和值、跨度、间距和四类直方图56状态 | 947个多余目标组合不用作合法像；映射不产生预测信息 |
| 协同交集 | 多条件交集、逐刀实际新增过滤与重叠、恢复排序 | 精确计算全集，拒绝用独立性假设乘过滤比例 |

### 新增历史N期自动反延续

针对**历史不变指标**支持 `repeat`（连续重复）、`arithmetic`（非零公差等差）、`alternating`（两态交替）、`periodic`（周期2—10）。只有符合严格模式时才生成一条实验性反延续规则。所有规则计算都以“目标期之前的历史”为输入，回测时每一期重新激活。历史不足不启用；理论延续值不可达则不给出无意义的过滤。

历史热度和马尔可夫属于动态训练模型，不允许将完整样本拟合的分数当成过去每期已有的静态时序指标。它们可作为开奖前拟合的**实验评分特征**。

### 全部100000注真实精确枚举（不涉及期开奖数据）

五条固定示例规则按顺序新增排除：37052、1120、5820、4068、400注，最后剩51540注、压缩48.46%。此结果可由本地代码重新计算；所谓“几刀通常能剩几百注”没有得到这个例子的支持。

### 使用CLI

进入已安装的 `D:\pl5\research_backend_v24` 后：

```powershell
uv sync --python 3.12 --group dev
uv run python research_v24.py cards --report reports/capabilities_v24.json
uv run python research_v24.py describe --family mod3 --metric road_key
uv run python research_v24.py run --history data/official_history.csv --rule-json examples/v24_rules.json --temporal-json examples/v24_temporal.json --budget 100 --report reports/v24_result.json --numbers reports/v24_candidates.csv
uv run python research_v24.py backtest --history data/official_history.csv --rule-json examples/v24_rules.json --temporal-json examples/v24_temporal.json --backtest-periods 10 --report reports/v24_backtest.json
uv run streamlit run phase2_app.py
```

`data/official_history.csv` 必须是用户自己核验过来源的CSV，字段建议为 `issue,date,number`。工具不会把演示数据当作官方开奖，也不会自动下载数据。本期代码不修改原GitHub主分支，独立页面在Streamlit左栏第12页；完整“五序”React前端的原生整合尚需另行适配。

如果要单独运行实验示例：

```powershell
uv run python research_v24.py demo --report reports/demo_v24.json --numbers reports/demo_candidates_v24.csv
```

### 实验输出的两个候选名单

- `strict_numbers`：严格符合所有规则的号码，数量不足时**绝不从已删除号码或外部大底之外补足**。
- `ranked_numbers`：基于违反规则条数（越少越先）、固定种子打破并列的启发式研究排序，允许从被过滤候选中按需“回捞”；不代表已校准中奖概率。

如果保留K个不同号码，公平独立开奖下一期至少精确命中一个的概率始终是 `K/100000`，与历史是否出现某个模式无关。每个规则的 `affected_count/100000` 是在公平零假设下的**集合大小**，不是未来延续概率下降的证据。

### 实验接口

研究HTTP服务 `integration_server.py`（回环地址 `127.0.0.1:8765`）：

- GET `/api/esse/spaces-v24/capabilities`：九空间UACP风格研究能力卡。
- POST `/api/esse/spaces-v24/evaluate`：接收历史号码、静态规则、时序规则、输出预算和固定种子，返回研究评分与逐刀审计；最多24条静态规则、12条时序规则、10000期历史、100注输出。

此接口不接受代码、不做外部执行、不发布正式选号算法。要让GitHub React前端访问，应继续通过已存在的同源Node桥接逻辑进行受控代理，不能开放CORS或公网接口作为替代。

## Windows安全安装

1. 解压完整ZIP，运行 `install_to_D_v24.bat`。
2. 后端会复制到 `D:\pl5\research_backend_v24`，已存在该目录则停止，避免覆盖。
3. 运行 `验证_V24.ps1`；启动Streamlit用 `启动_V24_九空间工作台.ps1`，启动桥接服务用 `启动_V24_科研接口.ps1`。
4. 旧版本的data、runtime、旧科研后端与GitHub五序前端不删除、不覆盖；本版默认**不**启用计划任务。

## 质量与边界

- 25项九空间、时序模式与HTTP专项测试已验证成功；另有CLI与前端环境边界测试。
- 全量旧版回归在约90%时因为旧测试运行时间太长而超时，不能报告全套通过。
- 未在本环境联网获取或校验最新官方开奖，未执行Windows安装、实际前端浏览器测试或真实未来开奖验证。
- 无任何已证实的预测优势；不得宣称100注能保证10期内中奖。
