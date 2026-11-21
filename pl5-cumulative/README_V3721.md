# PL5 V3.7.21 — 反例驱动元算子进化与拒绝机制（研发版）

本版本从 V3.7.20 完整累计包衍生，历史源码、归档、前向封存原件保持不变，新增独立的 `meta_operator_v3721` 研究模块。**这是受人类设计的有限语法约束的派生算子搜索**，不能称为 AI 自主发现新的基础数学定律，更不意味着对独立随机的彩票开奖有预测优势。

## 发现了什么？

旧 V3.7.20 有两个特征仿射组合的候选库，难以有效拟合 `((a+b)^2+3) mod 10` 等任务。本版本根据训练坐标的输入纤维一致性与旧模型训练反例，动态考察新的 `q(x)=(u*x*x+v*x+w) mod 10` **元算子族**：

1. 只读取训练数据，扫描多个已有安全输入特征的纤维冲突：相同 `x` 出现不一致 `y` 时，拒绝提出 `x → q(x)` 一元结构假设；每个候选输入特征须至少有6个不同观察值。
2. 在既有白名单常数集合 `(0,1,2,3,5,9)` 约束内学习 `u,v,w`；`u != 0` 确保测试新型二次表达能力；按训练错数、AST节点数、确定性规则排序并去重。
3. 将候选表达式编译为旧系统的受限 AST（节点不超过15、深度不超过8），以旧 `FrozenOperator` 格式保存。没有 `eval/exec`、动态解释来自数据的程序或联网调用。
4. 自动标出旧组合模型错而新模型对的训练反例。验证关口不能访问持出标签：选择验证误差最小的一个候选，若超出零误差阈值或不同整体行为的模型平局，**主动弃权**。
5. 唯一候选冻结后再执行一次持出测量，不允许重复结算或根据持出结果重新选模型。证据用 SHA256 做本地改动检测，不是第三方签名时间证明。

## 运行环境

- Python 3.12+，安装依赖：`python -m pip install -e ./research_backend pytest`。
- 在解压包根目录运行，Windows PowerShell 可把路径斜杠换成 `\`；不会访问 `D:\pl5` 或自动投注。

### 先产生演示用合成数据（60/20/20）

```bash
python research_backend/research_meta_v3721.py demo-split --case square_sum --seed 3721 --out runs/my_v3721/square
```

### 三道关口须分别运行

```bash
python research_backend/research_meta_v3721.py propose --train runs/my_v3721/square/training.json --study runs/my_v3721/study
python research_backend/research_meta_v3721.py freeze --study runs/my_v3721/study --validation runs/my_v3721/square/validation.json
python research_backend/research_meta_v3721.py evaluate --study runs/my_v3721/study --holdout runs/my_v3721/square/holdout.json
```

已在包内保存的25组演示证据在 `runs/v3721/benchmark/`，包含每期（任务、种子）的原始分割数据、候选 AST、训练失败记录、冻结选择和测试结果。整体摘要：`runs/v3721/benchmark/summary.json`，逐任务CSV：`results.csv`。

可使用如下命令**重新执行一份**不同位置的演示（默认路径已被历史结果占用，因此须指定新目录）：

```bash
python scripts/run_v3721_benchmark.py --out runs/my_v3721_replay
```

## 25组开发期合成任务结果

| 任务 | 5组中冻结通过 | 新模型持出错误/累计评分格 | 旧两特征仿射候选持出错误/100格 | 说明 |
|---|---:|---:|---:|---|
| `square_sum` | 5 | 0/100 | 68/100 | 使用 `(a+b)^2+3` 目标 |
| `quadratic_difference` | 5 | 0/100 | 71/100 | 使用 `(a-b)^2+2(a-b)+5` |
| `linear_sum` | 5 | 0/100 | 0/100 | 旧线性算子保留优势 |
| `cubic_sum` | 0 | 不评分 | 38/100 | 超出本次假设族，5/5弃权 |
| `iid_null` | 0 | 不评分 | 94/100 | 随机独立表，5/5弃权 |

注意：**旧方法只是“两个特征仿射组合”基线，不是 V3.7.20 全套基线；两者也未采用等计算预算。** 任务和种子均在开发时固定并在当前代码库生成，不是真正的外部盲测数据。0错不表示对未见过的随机真实过程可预测。二次变换是已知数学运算的组合，这里只证明**让程序自己选择输入特征、二次形式和参数**的工程能力。

## 验收与科研红线

- 不修改 26295 期任何本地或 GitHub 已公开封存内容；本版本不进行26295期结算。
- 不改旧过滤算法，新增候选仅存 `research-only` 文件夹；没有投注入口。
- 已运行33项新测试（包括5种子正/负任务、泄漏、证据篡改、一次数验收及随机拒绝）。全量历史测试验收结果另见 `docs/v3721/TEST_REPORT.md`。
- GitHub 没有自动推送或合并，Windows `D:\pl5` 实机验证尚未执行。

## 校验

```bash
python scripts/verify_v3721.py --root .
```

校验文件的 SHA256 和历史封存原件相同，仅证明原件被保留、文件未发生意外变化；不能保证原始历史完整性、第三方来源真实性或科学结论。下一步需要预注册**独立外部数学任务族**，然后再研究发现真正未知的表达式结构与自动拓展语法，并对等计算资源比较旧版算法。
