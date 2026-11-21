# PL5 V3.6 合并研究包（V3.4 累计后端 + V3.5/V3.6 新增研究模块）

基础：用户提供的 PL5_V3.4.zip，保留原始目录及历史版本资料。
新增：research_backend/pailie5/filter_validation_v35.py、nca_v36.py、tests/test_v35_v36_integration.py。
版本：research_backend/pyproject.toml 从 3.4.0 更新为 3.6.0（集成包研究版本）。

## 本轮验证
Python 3.13 环境（项目要求 >=3.12）：
`cd research_backend && python -m pytest -q tests/test_parameter_hub_v34.py tests/test_transfer_evolution_v34.py tests/test_parameter_http_v34.py tests/test_v35_v36_integration.py`
结果：29 passed in 2.74s。

## 范围和限制
- V3.5：固定保留/排除预算的误删率评估，不自动激活正式过滤。
- V3.6：独立外部数字关联的简单模10算子选择、训练/测试隔离和信息可用性校验；不是开放式数学语言进化的完整实现。
- V3.4 历史原有源码与文档原样保留（除项目版本号）。
- 本轮未运行全部历史测试、Windows安装、Streamlit/HTTP端到端或 GitHub React 前端联调。
- 未使用真实官方开奖数据，未证明任何彩票过滤优势。
- 不能把这个集成包视为所有 V1.x–V3.6 功能均已验收的正式发布版本。
