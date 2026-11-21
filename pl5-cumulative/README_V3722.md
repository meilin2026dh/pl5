# PL5 V3.7.22 — 分角色科研验证与有限语法扩展（科研原型）

本包从 V3.7.21 累计源代码继承，保留全部原始源码、实验、历史封存文件。本版**只在研究隔离模块**新增“独立合成出题→训练提出有限映射算子→挑战集寻找反例→验证冻结或弃权→一次持出评估”的实验路径。**未接入真实选号、未自动投注，未证明开奖预测优势。**

## 本版解决的具体问题

V3.7.21 的新算子搜索只针对开发者规定的二次多项式 `u*x²+v*x+w mod 10`。V3.7.22 允许研究程序从训练样本中选择受限输入特征，**自归纳有限域一元映射表**，而不是再预设表达式必须是二次式；因此能够表示三次、阶梯、奇偶等非线性映射。但这是一类已知的数学表示（有限查找表），不是凭空发明新的基础数学运算，也不保证适用于比0—9更大的输入空间。仍受人类定义的输入特征白名单限制。

- `研究出题器`：生成已知合成任务；将100个坐标拆为55训练、15挑战、10验证、20持出，四部分不重合。来源、算法和随机种子可复现。**任务族在源码中可见，不属于外部未知盲测**。
- `表达创造器`：只能收到训练观测，比较13个已登记输入特征的纤维一致性，生成允许的`learned_unary_table_v1`派生算子。未见过的输入保持`null`，绝不推测其标签。
- `证伪器`：针对候选在独立挑战集上记录相反观测（包括输入覆盖不足），阻止被反例否定的候选晋级。
- `冻结评审器`：仅在反例挑战后使用验证集选取模型；多个行为不一致的候选并列时弃权。有限域性质证书由**独立的整数标量实现**复算100个输入，检查其与NumPy执行一致，并判断有限域交换性、幂等性等性质（**不是对无限域的数学定理证明**）。
- `持出评估器`：只允许执行一次，模型不再根据测试标签修改，若弃权则不计算持出命中率。
- `新一轮反例驱动修订`：`revise`可将先前挑战数据**重新归类为新一轮训练**，构造下一轮候选；必须使用全新独立的挑战和验证关口，**不允许直接使用旧持出集验收修订后的模型**。

分角色是代码级的数据传递契约，不是多个远程大模型，也不能阻止拥有所有本地文件访问权限的进程人为读取未开放数据。校验摘要是**本地SHA256防误改**，不是可信第三方时间戳。

## 建议运行环境

推荐 Python3.12+。在解压后包根目录安装：

```powershell
py -3.12 -m pip install -e ./research_backend pytest
```

Linux或macOS可用 `python -m pip install -e ./research_backend pytest`。首先运行新增测试：

```powershell
py -3.12 -m pytest -q research_backend/tests/test_language_evolution_v3722.py
```

### 完整的五步实验

```powershell
py -3.12 research_backend/research_language_v3722.py create-task --family cubic_sum --seed 9931 --out runs/my_v3722_task
py -3.12 research_backend/research_language_v3722.py invent --train runs/my_v3722_task/training.json --study runs/my_v3722_study
py -3.12 research_backend/research_language_v3722.py falsify --study runs/my_v3722_study --challenge runs/my_v3722_task/challenge.json
py -3.12 research_backend/research_language_v3722.py freeze --study runs/my_v3722_study --validation runs/my_v3722_task/validation.json
py -3.12 research_backend/research_language_v3722.py evaluate --study runs/my_v3722_study --holdout runs/my_v3722_task/holdout.json
```

每次实验文件都只能新建，不能覆盖。想要重现35组开发期演示，可另选一个**不存在的**输出路径：

```powershell
py -3.12 scripts/run_v3722_benchmark.py --out runs/my_v3722_replay
```

若想构造下一轮新的候选：

```powershell
py -3.12 research_backend/research_language_v3722.py revise --study runs/my_v3722_study --train runs/my_v3722_task/training.json --challenge runs/my_v3722_task/challenge.json --new-study runs/my_v3722_revision
```

注意：修订后原挑战已成为训练事实；不能直接用于新研究的`falsify`或重用旧`holdout`来宣称独立验证。需要由新出题者提供未来的、独立的数据关口。

## 35组开发期合成任务结论

每种任务5个确定性随机种子。24组冻结并通过最终测试，11组弃权；已冻结任务合计480格持出测试中0个错误，**并不是35组任务整体的零错误**。20组分别属于三次和、阶梯和、二次差、奇偶差任务；三次乘积4组通过、1组因无法覆盖必要输入而弃权；随机噪声及复杂交互共10组全部弃权。

**证据级别**：开发者设计的合成任务；训练、挑战、验证和测试分离但分布与问题类别都已知。不能用于宣称预测真实开奖、跨数学领域泛化或拥有通用的自主数学发现能力。V3.7.21比较器并未配平计算预算，本版不宣称在公平基准上超越旧版。

完整证据位于`runs/v3722/benchmark/`；可复验摘要是`results.csv`、`summary.json`。工程验收见`docs/v3722/TEST_REPORT.md`。

## 研究红线和下一阶段

- 原 V3.7.19 26295期封存原件不修改，本版不对该期做开奖后结算。真实彩票数据与有限域合成任务**完全分离**。
- 不修改V3.7.21及更早旧算法源码，只增加独立研究模块和版本入口；不得将本研究版模型接入自动选号生产入口。
- 下一步应由**外部人员/独立系统**事先提供未公开任务和任务哈希，在独立进程及权限下按固定预算进行盲测；进一步学习跨任务可迁移的**简洁算子程序**，而不仅仅是记忆0—9映射表。
- Windows `D:\pl5`尚未获得实际访问，Windows实机验收、GitHub推送和前端构建单列，禁止代称已完成。
