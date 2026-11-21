# PL5 V3.7.16 — 研究流程端到端位图加速

基于V3.7.15累计源码扩展；**既有接口默认采用NumPy，不改变过滤数学语义、不宣称中奖概率提升。**

## 已接入现有流程

- `pailie5.basic_filters.combine_basic_and_pattern(...,basic_catalog=...)` 基础+时序规则交集
- `pailie5.probability_ranker.rank_all_numbers(...,basic_catalog=...)` 10万注排序与基本条件标记
- `pailie5.probability_ranker.rolling_rank_backtest(...,basic_constraints=...,basic_catalog=...)` 历史前向滚动排序
- `pailie5.sculpting.knives_from_history(...,basic_catalog=...)` 基础条件雕刻刀生成
- `pailie5.sculpting.rolling_sculpt_backtest(...,basic_catalog=...)` 历史前向雕刻研究

共享会话：

```python
from pailie5.basic_filters import BasicConstraint, combine_basic_and_pattern
from pailie5.basic_filter_catalog_v3716 import BasicFilterCatalog

rules = [BasicConstraint('sum', minimum=10, maximum=30),
         BasicConstraint('odd_count', minimum=1, maximum=4)]
catalog = BasicFilterCatalog(rules)
ids = catalog.select(rules)
# 带 basic_catalog=catalog 调用上述科研函数可跨次复用静态条件位图。
# 自定义指标更新后必须显式 catalog.refresh('indicator:指标名')。
```

## 实验

命令在 `research_backend` 目录中运行：

```bash
python -m pytest tests/test_bitmap_pipeline_v3716.py tests/test_bitmap_workflow_benchmark_v3716.py -q
python benchmark_bitmap_workflows_v3716.py --repeats 15 --seed 3716 --output ../docs/v3716/benchmark_replay.json
```

实验使用`research_backend/data/synthetic_demo.csv`合成历史数据，只能证明在原有科研程序的执行流程中，新旧计算结果一致，并量化端到端CPU时间。数据**不是经过认证的真实开奖历史**。

## 边界

- 位图只缓存静态基础条件；不得跨期缓存历史依赖规则。
- 已编译基础位图占用更多缓存内存（20项理论250KB）。
- 冷启动与热缓存分别报告。若单次流程不复用大量规则，可能变慢。
- 没有直接修改用户Windows电脑`D:\pl5`，亦未完成Windows实机测试。
- GitHub源码研究分支与完整累计包可能不同步；以交付zip和验收清单为准。
