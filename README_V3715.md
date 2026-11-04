# PL5 V3.7.15 科研预览版：GA-CS条件组合优化

这是一套完整累计科研源码（继承V3.7.14，新增GA/CS/GA-CS/随机/退火/贪心六种相同预算的搜索器），**不是已部署的预测服务**。

## 新增模块

- `research_backend/pailie5/ga_cs_optimizer_v3715.py`：`SearchProblem`、`evaluate_genome`、`optimize`，用20个既有硬条件的精确位图优化启用子集，强制预算、硬约束保留、精英维护和CS Lévy大步长扰动。
- `research_backend/benchmark_ga_cs_v3715.py`：基于V3.7.14 `_rules()` 的20条真实PL5静态规则、100,000个号码进行固定预算对照；每个结果的全部号码使用原 `apply_basic_filters` 独立核对。
- `research_backend/tests/test_ga_cs_optimizer_v3715.py` / `test_ga_cs_benchmark_v3715.py`：TDD验收，包括相同注数但不同号码的静默错误回归。
- `docs/v3715/benchmark_verified.json`：6方法 × 8种子 × 300次评估 × 2场景，完整原始结果。
- `docs/v3715/robustness_results.json`：6方法 × 12新种子 × 300次评估 × 3目标的压力检验。
- `docs/v3715/REPORT.md`：实测、限制、验收及完整复现说明。

## 实验目的与技术边界

本轮只使用静态硬条件的**子集选择**，CS在二值启用向量上执行Lévy飞行翻转位；未实现可调软规则的连续权重优化（硬条件绝不可变成软权重）。优化目标是保留注数接近预设的工程目标并惩罚规则复杂度，不导入真实历史开奖号码，不主张预测有效。

20条规则的交集尚保留28,672注，所以100注目标**严格不可行**；所有方法必须报告不可行。

`pyproject.toml`保留原平台版本标识，研究版编号并不代表已正式发版。当前没有Windows真实验收，也没有部署到 `D:\pl5`。

## 运行

```powershell
cd D:\pl5-v3715\research_backend
py -3.12 -m pip install -e ".[dev]"
py -3.12 -m pytest tests\test_ga_cs_optimizer_v3715.py tests\test_ga_cs_benchmark_v3715.py -q
py -3.12 benchmark_ga_cs_v3715.py --output ..\docs\v3715\benchmark_windows.json --evaluations 300 --seeds 0 1 2 3 4 5 6 7
```

上述命令仅为Windows本地安装后的运行步骤，**本轮实际实测环境为容器Linux/Python 3.13**；请勿混淆。
