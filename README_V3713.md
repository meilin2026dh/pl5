# PL5 V3.7.13 — 覆盖数组 / 多重等重码 / 共形风险体检

科研工具扩展版，**基于 V3.7.12 全部源码累计**。不修改旧版代码与旧实验结果；新增模块已纳入 `research_backend/pailie5`，可通过 Python import 和单次 CLI 运行。

## 实现内容

| 模块 | 关键接口 | 作用 |
|---|---|---|
| `covering_arrays_v3713.py` | `generate_pl5_covering_array`, `audit_interactions` | GF(11)代数强度2/3覆盖数组 + 独立交互审计 |
| `codebook_v3713.py` | `encode_one_hot`, `select_diverse_codebook`, `audit_codebook` | 5块×10位独热编码、码重5、最小汉明距离、分散度与覆盖率联合优化 |
| `conformal_audit_v3713.py` | `calibrate_rank_cutoff`, `assess_future_ranks`, `audit_fixed_filter` | 冻结模型的分割共形排名阈值、真正独立后验评估、精确误删风险上界 |
| `research_v3713.py` | `codebook`, `conformal`, `fixed-filter` | 文件输入输出，冻结实验、机器可读报告 |

## 复现实验（Windows PowerShell / Python 3.12+）

```powershell
cd research_backend
py -3.12 -m pip install -e '.[dev]'
py -3.12 research_v3713.py codebook --strength 2 --budget 100 --min-distance 3 --output ..\runs\v3713\codebook
py -3.12 research_v3713.py conformal --input ..\docs\v3713\demos\conformal_input_synthetic.json --output ..\runs\v3713\conformal_audit.json
py -3.12 -m pytest -q tests\test_covering_arrays_v3713.py tests\test_codebook_v3713.py tests\test_conformal_audit_v3713.py tests\test_research_cli_v3713.py
```

`codebook` 输出 `codebook.txt` 与 `audit.json`；若距离约束导致未满预算，`budget_fulfilled=false`，不填充重复号码。`conformal` 的真实输入必须使用**在校准前已经冻结**的模型、按时间严格区分训练/校准/测试的真实观测。输入中的 `model_sha256` 与 `precommitted` 只做字段验证/调用方声明，**程序无法证明它们真实可信**。

## 科研红线

- **覆盖数组**：全覆盖指数字位置交互，不指中奖；未证明构造是最小注数。
- **等重码**：PL5任何合法号码的50位独热编码重量本来就是5；提高分散度来自另加的最小码距。
- **共形预测**：可交换性、冻结评分规则、独立校准是边际覆盖理论成立的前提。单条过滤条件的二元命中记录仅用于风险审计，**不**自动获得共形保证。
- 公平、均匀且独立的PL5开奖：保留100注的单期精确命中概率仍为0.1%，不会因这些工具提高。
- 演示数据为人工构造，不是历史开奖；未进行 Windows 实机、线上React/Streamlit、真实开奖数据或GitHub部署验收。

## 新增：动态注数预算（`dynamic-budget`）

`dynamic_budget_v3713.py` 将事前冻结的单期难度尺度 `s_t` 和真实开奖号码在事前冻结评分器下的名次 `r_t` 组合为标准化不合规分数 `r_t / s_t`。在独立校准期取带 n+1 校正的分位数 `q`，建议单期目标注数 `N_t = min(100000, ceil(q*s_t))`。**只有归一化后的未来分数与校准分数满足可交换性等条件时，才有边际覆盖保证；它不是任意动态条件下的条件覆盖。**

资金上限 `B_t` 是硬约束：若 `N_t > B_t`，报告 `coverage_target_unaffordable`，实际可负担注数至多 `B_t`，不再宣称原来的覆盖保证。在公平独立开奖下，实际购买 `n` 个不同号码的头奖精确覆盖概率仍是 `n/100000`。`s_t` 必须在开奖前由冻结模型给定；文件自述的哈希、标签和前置承诺无法独立证实。

```powershell
cd research_backend
py -3.12 research_v3713.py dynamic-budget --input ..\docs\v3713\demos\dynamic_budget_input_synthetic.json --output ..\runs\v3713\dynamic_budget.json
```

JSON中 `calibration_ranks`、`calibration_difficulty_scales`、`calibration_issues` 是独立校准期的排名、正整数难度尺度和期号；`future_issues` 包含未来期号、难度尺度与 `affordable_max_tickets`；可选 `holdout` 仅用于揭晓后审计。预算不可行不能通过 `max(B_t,N_t)` 擅自加注；正确行为是报告目标不可达，再由用户选择降低覆盖目标、提高自愿资金上限或暂不参与。
