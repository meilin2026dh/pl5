# PL5 V3.7.20：自主数学发现与反例驱动验证（研究版）

本版在 **V3.7.19 第三阶段完整累计包**上追加研究模块，旧算法、历史归档和26295期封存原件原样保留。新增数学表达式的**训练—验证—测试三道关口**、参数搜索与反例档案；它是固定安全语法下的结构发明原型，不是通用基础数学原理发现器，更不是彩票预测优势证明。

## 核心创新与界限

1. 使用已有 `structure_ast_v372` 和 `structure_search_v372` 的白名单 AST，自动枚举多特征合成结构：两特征线性组合（模10）、6组候选系数与常数偏移。参数只根据训练格拟合。不会加载用户代码，也不执行任意表达式。
2. 组合式假设不局限于已有预设的10种目标公式；新表达式相对**本次候选库**可视为结构创新，但所有原子算子来自既有白名单。
3. 用训练失败坐标和预测偏差建立反例记录。训练误差下降不等于泛化成功，下一道关口使用新的验证格筛选候选。
4. 把验证胜出的表达式封存为既有 `FrozenOperator` 格式，在第三道关口以新的持出格进行一次性评测，不得改选、重复结算或篡改证据。
5. 单次实验采用本地、模拟分割；对于随机 IID 控制，不应期待存在可压缩预测结构。任何形式的的彩票胜率/收益结论均不允许导出。

## 运行要求

- Python 3.12+。安装：`python -m pip install -e ./research_backend pytest`；Windows可用 `python -m pip install -e .\research_backend pytest`。
- 工作目录是解压后的**包根目录**，下述命令在 Linux、macOS、Windows PowerShell 都可在 Python 环境下运行。
- 全流程**不联网**，不会向本地 `D:\pl5` 自动安装或做彩票投注。

### A：生成合成任务训练/验证/测试文件

```bash
python research_backend/research_math_v3720.py demo-split --case composite_absproduct --seed 3720 --out runs/v3720/demo
```

案例可选：`composite_absproduct`（`(a*b+abs(a-b)) mod 10`）、`shifted_square`、`iid_null`（独立随机表）。每个任务训练60格、验证20格、最终测试20格。示例在本机生成全部标签，所以**不是外部独立盲测**。

### B：仅用训练数据生成候选并记录反例

```bash
python research_backend/research_math_v3720.py propose --train runs/v3720/demo/training.json --study runs/v3720/demo/study --budget 1200 --top-n 16
```

### C：只用验证数据筛选并冻结唯一表达式

```bash
python research_backend/research_math_v3720.py freeze --study runs/v3720/demo/study --validation runs/v3720/demo/validation.json
```

### D：只允许一次的独立测试评分

```bash
python research_backend/research_math_v3720.py evaluate --study runs/v3720/demo/study --holdout runs/v3720/demo/holdout.json
```

每阶段单独运行，不提供“一键拟合并偷看测试集”的 API。所有研究工件默认使用独占写入，发现文件已存在即拒绝覆盖。保存的 SHA256 用于本地一致性验证；**不能替代外部时戳、签名和可审计的公开预注册证据**。

## 实测结果（受限合成任务）

| 任务 | 枚举参数化构成 | 原搜索训练错误/60 | 创新搜索训练错误/60 | 验证错误/20 | 持出错误/20 |
|---|---:|---:|---:|---:|---:|
| 复合模10运算 | 11,550 | 35 | 0 | 0 | 0 |
| 平方结构（边界测试） | 11,550 | 44 | 32 | 12 | 15 |
| IID随机表（负对照） | 11,550 | 45 | 42 | 16 | 18 |

基于开发期选定的3个任务，不允许把其中的20格视为独立研究论文的确认性样本。未来要用全新任务族、多种种子、严格封存、实验预算匹配、负对照及多重检验评估是否存在可重复的算法改进。

## 新增文件

- `research_backend/pailie5/math_discovery_v3720.py`：训练-only组合发明、候选冻结与测试评估。
- `research_backend/research_math_v3720.py`：三关口 CLI。
- `research_backend/tests/test_math_discovery_v3720.py`：泄漏、重放、完整性、可复现与随机空白对照测试。
- `docs/v3720/`：运行证据、版本审计与测试报告。
- `runs/v3720/`：结构案例和随机空白对照的独立实验记录。

## 研究准入原则

研究候选表达式只可进入隔离的 **research-only** 候选库；不能自动投用到真实彩票开奖选号。彩票时间序列统计与10x10数学运算表的推断属于不同问题，数学表达式在合成任务上的正确率不会转化为彩票预测概率。

后续建议：建立未用于开发的独立数学运算族挑战集（至少几十个独立任务），采集多次随机种子、记录检验家族与比较预算，再研究多智能体共享失败反例和元算子提案；另行开展26295期之前已经公开的封存审计与开奖后结算，严禁修改既有候选集。

## 完整包校验

在包根目录执行：

```bash
python scripts/verify_v3720.py --root .
```

从第三阶段包升级可使用独立补丁，但必须先核对第三阶段完整包 SHA256；直接全量解压更稳妥。
