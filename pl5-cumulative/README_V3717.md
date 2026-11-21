# PL5 V3.7.17 — 科研任务端到端加速与前向验收

**完整累计研究包**。本版在V3.7.16原有源码和研究结果上增量添加，保留旧默认流程。

## 新增可选参数

- `pailie5.probability_ranker.rolling_rank_backtest(..., target_only=True)`
- `pailie5.sculpting.rolling_sculpt_backtest(..., target_only=True)`
- `pailie5.pattern_rules.filter_next(..., optimize_context=True)`

前两项仍对完整10万注排序，只在完成排序后查询实际开奖号，跳过完整10万行Pandas报告构建。第三项仅在当期调用中共享同一跨期指标，**不跨期缓存历史**。所有开关默认False。

## 可重复测试

```bash
cd research_backend
python -m pytest -q tests/test_target_only_v3717.py tests/test_research_performance_v3717.py
python benchmark_research_performance_v3717.py --seed 3717 --repeats 10 --output ../docs/v3717/benchmark_rerun.json
python -m pytest -q tests
cd ..
python -m pytest -q integration_tests
```

实验结果位于 `docs/v3717/benchmark_seed3717.json` 和 `benchmark_seed3718.json`，技术报告见 `docs/v3717/REPORT.md`。

本次数据源仅为内置**合成历史数据**，不能解读为认证真实彩票预测测试；默认旧代码路径仍然不变。源码未部署到用户的Windows `D:\pl5`。
