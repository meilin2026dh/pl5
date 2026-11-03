# PL5 V3.7.14 — 高通量精确位图过滤执行层

**研究预览版，基于 V3.7.12 累计源码和 V3.7.13 的覆盖数组、等重码、共形校准源码继续扩展。**

## 新增

- `research_backend/pailie5/high_throughput_v3714.py`
  - 00000 至 99999 全域的 100,000 位精确位图，每条规则逻辑占 12,500 字节。
  - `ExactFilterEngine.add_basic()` 将既有 `BasicConstraint` 编译为缓存位图。
  - `add_vector()` 接入可信向量化规则；`add_mask()` 冻结已有布尔掩码；`add_deferred()` 延后昂贵的精确逐注检查。
  - `evaluate(all_of=..., any_of=..., none_of=...)` 精确AND/OR/NOT逻辑运算；延期规则只能用于AND。
  - `add_basic(...,replace=True)`、`remove()`、`invalidate('dependency')` 精确维护缓存。
  - `stats()` 输出已编译规则数、逻辑内存、Python实际整数内存与调用计数。
- `research_backend/benchmark_high_throughput_v3714.py` 以原 `apply_basic_filters()` 作为独立结果对照，输出20条件、100,000注、可复现JSON性能记录。
- `research_backend/tests/test_high_throughput_v3714.py`、`test_high_throughput_benchmark_v3714.py` 精确性、安全更新、混合条件与性能实验正确性检查。
- `docs/v3714/DESIGN.md`、`REPORT.md`、`benchmark.json`、`VERIFICATION.json`。

## 运行

从包内 `research_backend/` 目录启动：

```powershell
py -3.12 -m pytest tests/test_high_throughput_v3714.py tests/test_high_throughput_benchmark_v3714.py -q
py -3.12 benchmark_high_throughput_v3714.py --output ..\docs\v3714\benchmark_local.json --repeats 20 --seed 3714
```

最低运行要求Python 3.12，NumPy与pytest。**正式性能验收必须在目标Windows电脑上重新测量**；本交付中的性能数字为Linux/Python 3.13运行环境。

## 有意未实现

- 无Bloom Filter：对十万固定号码使用布隆过滤器会有假阳性且需要预建集合；精确位图更适合这个规模。
- 未改动上游复杂预测模型或其未来训练数据来源，也未将性能收益误报为彩票命中收益。
- 未实现自动检测任意外部状态变化：更新外部时间序列/自定义指标后，必须明确 `invalidate`，否则缓存会过期。

## 风险提示

这是工程性能优化。各类过滤集合的数学覆盖面与真实彩票中奖概率是不同问题。准确性在测试环境中以旧版NumPy过滤器为基准，并不证明任何统计预测优势。