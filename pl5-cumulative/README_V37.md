# PL5 V3.7 研究原型（增量版）

以 V3.6 累计代码为基础，新增 `research_backend/pailie5/math_language_v37.py` 和 `research_backend/tests/test_math_language_v37.py`。

## 功能
- 有界数学表达式搜索：模10仿射、异或偏移、绝对差偏移；共1020个候选表达式。
- 10×10 运算表精确重建与未观测单元诊断。
- 交换律、结合律、双侧单位元的穷举验证。
- 不同运算表间的表达式复用检验。

## 验证
在隔离目录运行 `python -m pytest -q tests/test_math_language_v37.py tests/test_v35_v36_integration.py`，10项通过。全量测试运行超时，未取得全量通过证明。

## 限制
本原型并非开放式数学发明；没有发现彩票预测或过滤优势。现有生产过滤默认不启用本模块。
