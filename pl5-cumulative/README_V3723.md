# PL5 V3.7.23 — 历史数学算子压缩与跨任务迁移（科研原型）

本版直接继承 V3.7.22 完整累计包，在**科研隔离模块**实现：将 V3.7.22 已完成训练、挑战、验证与持出评分的有限映射算子，压缩为白名单内的简短数学程序；作为只读迁移模板，在独立新任务中仅学习少量目标参数，通过另一批验证数据冻结，最后一次性测试持出数据。

**核心边界：**这是有限数字域 `a,b ∈ {0,…,9}` 内的受限程序归纳与同族迁移。没有发明新的基础数学运算，没有进行外部任务盲测，没有证明彩票可预测。不可运行输入提供的任意 Python 源码。

## 技术组成

- `research_backend/pailie5/transfer_language_v3723.py`：源证据认证、有限查找表压缩、冻结模板库、目标参数拟合、模型选择/弃权、完整性校验、持出一次性评估及可选的盐化SHA256承诺。
- `research_backend/research_transfer_v3723.py`：命令行接口。训练和冻结命令不接收测试标签。
- `scripts/run_v3723_benchmark.py`：开发者设计的合成数据基准，明确不属于外部盲测。
- `research_backend/tests/test_transfer_language_v3723.py`：泄漏、篡改、重测、压缩精确性、陌生结构及拒绝机制的自动化测试。
- `runs/v3723/benchmark_final/`：48组实验的原始数据、阶段证据、CSV与汇总，能够重放；只保留最后一组主实验。

## 程序压缩

对V3.7.22已完整认证的映射表，穷举**固定白名单**：常数、奇偶分类、单一阈值、1/2/3次有限域多项式，挑选与原映射完全等价且“参数数量编码位数代理指标”更少的程序。编码代理不是严格最优通用MDL；模型仍然限定在白名单内。

已获认证的4类源模板：三次和、单阈值、二次差、奇偶差。迁移时只复用模板输入特征与源程序，目标任务仅学习 `scale∈{1,3,7,9}` 和 `shift∈{0,...,9}`。不跨越未见任务类别做零样本准确率主张。

## 开发期验证摘要

每类6个确定性种子，共48个合成任务：同族参数变化4类×6=24，全部冻结并在56个独立测试格中无误（24×56=1,344格）；随机、陌生交互、阈值变化、训练标签单点破坏4类×6=24，全部拒绝模型。*此结果仅涵盖被接受的任务，并受生成设定强烈影响。*

同样目标数据上，使用已知源特征的简易查表对照在1,344格里共遇到102格未观察输入，提示程序压缩能够在这组同族设定中提供有限域覆盖能力；此对照不是完整V3.7.22引擎，也未配平源发现成本或总算力，不能据此认定端到端胜出。

## 推荐命令（解压后根目录执行）

```powershell
py -3.12 -m pip install -e ./research_backend pytest
py -3.12 -m pytest -q research_backend/tests/test_transfer_language_v3723.py
py -3.12 scripts/run_v3723_benchmark.py --out runs/my_v3723_replay --seeds 6
```

对已有V3.7.22完整认证的**多个源研究**，创建冻结库：

```powershell
py -3.12 research_backend/research_transfer_v3723.py certify-bank --source-study runs/v3723/benchmark_final/sources/00_study --source-study runs/v3723/benchmark_final/sources/01_study --source-study runs/v3723/benchmark_final/sources/02_study --source-study runs/v3723/benchmark_final/sources/03_study --out runs/my_bank.json
```

可选的外部任务承诺协议（示意）：

```powershell
# 只有独立出题者读取测试集，并私下保留长度至少16位的随机nonce。
py -3.12 research_backend/research_transfer_v3723.py commit-holdout --holdout PATH_TO_HIDDEN_HOLDOUT --nonce SECRET_RANDOM_NONCE
# 把公开的64位摘要交给研究者，真实测试标签不公开。
py -3.12 research_backend/research_transfer_v3723.py fit-target --train PATH_TO_TRAIN --bank runs/my_bank.json --study runs/my_transfer --commitment PUBLIC_SHA256
py -3.12 research_backend/research_transfer_v3723.py freeze-target --validation PATH_TO_VALIDATION --bank runs/my_bank.json --study runs/my_transfer
# 出题者在研究冻结后首次提供持出数据与原nonce，执行一次性评分。
py -3.12 research_backend/research_transfer_v3723.py evaluate-target --holdout PATH_TO_HIDDEN_HOLDOUT --bank runs/my_bank.json --study runs/my_transfer --reveal-nonce SECRET_RANDOM_NONCE
```

盐化SHA256只能核对承诺与揭示的数据一致性；不能代替独立权限隔离、GitHub/RFC3161可信时间证明、对外独立出题，也无法防止拥有所有本地数据权限的操作者作弊。所有写入均使用新文件路径，拒绝覆盖已存在的证据。

## 未完成

- 外部人员预注册并生成的未知任务盲测尚未执行；真正跨类别泛化尚未证明。
- 与V3.7.11等已有迁移方案的**总计算预算**还未配平；此版的核心贡献是V3.7.22证据链与短程序迁移的集成，而非首次提出任务迁移。
- Windows `D:\pl5` 实机安装、Windows Python3.12回归、真实排列五前向预测效果及GitHub远端CI均未验收。
- 原V3.7.19第26295期已封存数据继续保留，**不进行事后修改或择优**。
