# PL5 V3.7.17 — 研究流程端到端加速

本分支用于登记 V3.7.17 的加速研究；**当前并非完整、可独立运行的 GitHub 代码发布**。

## 本次在完整累计科研ZIP中实现

- `pailie5/probability_ranker.py`: opt-in `rolling_rank_backtest(..., target_only=True)`，保持10万注全排序，跳过只用于取一行的10万行Pandas表格。
- `pailie5/sculpting.py`: opt-in `rolling_sculpt_backtest(..., target_only=True)`，完整保留雕刻和配额逻辑。
- `pailie5/pattern_rules.py`: opt-in `filter_next(..., optimize_context=True)`，按单期缓存重复计算的跨期特征，不跨期复用。
- `benchmark_research_performance_v3717.py` 与两个专项测试文件、完整性能报告。

## 两轮复现结果（合成历史，不是实盘数据）

| Workflow | seed 3717 | seed 3718 |
|---|---:|---:|
| 5期滚动排序 | 3.67× | 4.04× |
| 5期滚动雕刻 | 1.86× | 2.01× |
| 3期复杂时序规则分析 | 4.41× | 4.72× |

端到端60次新旧报告完全一致。原版默认调用保持不变。完整后端 **871/871**、历史集成 **29/29** 通过，累计 **900项**；独立解压重新验证新增12项和29项集成测试通过。

## GitHub缺口（未解决）

现存研究分支 `research/v3716-e2e-bitmap-integration` 仍没有同步全部累计基础源码，**本分支从它继承，不可单靠检出本分支运行完整Python后端**。本轮完整且有发布校验的交付物是对话中生成的 `PL5_V3717_Full.zip`。应先将该累计源码移植到隔离分支，核对哈希后合并，再运行GitHub检出环境的回归。

不宣称部署到用户Windows `D:\pl5`，不宣称提高彩票预测能力。
