# PL5 V3.7.1 增量研究补丁

基于 PL5 V3.7 研究预览版，新增有限运算表进化搜索与测试。

将补丁内文件覆盖式添加到 V3.7 对应目录（不要删除其他源码）。

测试：cd research_backend && python -m pytest -q tests/test_operator_evolution_v371.py

验证集只用于最终诊断，不用于选择算子。当前不宣称彩票过滤优势，不自动启用生产规则。

本轮仅完成 5 项新增测试，未执行历史全量测试，也未同步 GitHub。
