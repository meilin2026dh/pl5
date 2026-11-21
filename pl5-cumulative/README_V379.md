# PL5 V3.7.9 — 有界自适应耦合数学原语研究

这是建立在 V3.7.8 累计科研包之上的**增量研究版本**，不代表彩票预测能力或稳定的 Windows/React 部署版本。

## 新增科研代码

- `research_backend/pailie5/adaptive_primitives_v379.py`：在给定的8类耦合基函数、18个候选分段边界上进行训练期模型筛选，检查模型一致性与全10×10表可识别性。不确定时弃权。
- `research_backend/pailie5/adaptive_study_v379.py`：不可随意修改的合成实验协议、新独立种子任务、V3.7.8有限模型对照、结果汇总。
- `research_backend/tests/test_adaptive_primitives_v379.py`、`test_adaptive_study_v379.py`、`test_adaptive_adversarial_v379.py`：训练期泄漏、模型歧义、独立随机负对照、时间外推不作虚假声称等行为测试。
- `docs/v379/`：冻结协议、逐次实验、复跑与验收证据。

## 运行

```bash
cd research_backend
python -m pytest -q tests/test_adaptive_primitives_v379.py tests/test_adaptive_study_v379.py tests/test_adaptive_adversarial_v379.py
python -m pytest -q
cd ..
python -m pytest -q integration_tests
```

此版本不改变历史科研调度器默认运行行为，也不允许任何发现的算子自动进入真实选号过滤。2026-11-04起本研究版使用 `V3.7.9` 作为**科研发布标识**；旧 Python 项目元数据仍为 V3.7.6，因原来的版本锁定回归测试尚未迁移，不应把二者混为一个已经发布的软件版本。
