# PL5 V3.7.5 — 科学问题自主发现与跟踪引擎（累计版）

## 这版实际具备什么

建立在 V3.7.4 已验收的有界自主研究引擎之上，新增科学问题树、竞争性可证伪假设、实验优先级、跟进预算、强制随机负对照与只增不改的实验计划。每轮实验选择会根据新收集的证据调整；问题仍未获得外部科学确认。

**明确边界：** 目前是离线、有限结构集合和预设推理规则内的自主科研。**不是**开放式自主科学家，不能自动阅读论文、编写并执行自己创造的算法、修改源代码、证明数学定理或提高彩票命中率。无法解决的程序错误将暂停而不是自动修复。不得将合成结果当成彩票预测证据。

## 继续运行

在 Windows 上解压到新目录（或备份后增量合并），先检查依赖 Python 3.12+ 和项目依赖。双击 `RUN_V375_ONCE.cmd` 运行有界3轮。默认同 `runs/autonomous_v375` 内的前12轮完整记录继续，使用原始种子37401、每种策略预算500、每4轮强制随机负对照。新的协议在执行前锁定，旧冻结算子及历史实验不可覆盖。

也可以手动运行：

```powershell
cd D:\pl5\research_backend
py -3.12 research_scientific_v375.py --output ..\runs\autonomous_v375 --cycles 3 --budget 500 --seed 37401 --control-every 4
```

`SCHEDULE_V375_WINDOWS.ps1` 默认只预览；明确传入 `-Install` 才会注册本机每天02:00执行的有界实验任务。当前会话没有在你的Windows电脑安装或启用定时任务。

## 研究证据

- `runs/autonomous_v375/state.json`：12轮状态和问题标签。
- `runs/autonomous_v375/science/registry.json`：分层科学问题库（问题→假设→证据→状态）。
- `runs/autonomous_v375/science/plans/00009.json`起：预先冻结的科学问题和候选方案。
- `runs/autonomous_v375/cycles/00009/`起：原有4策略完整实验、冻结算子、保留评价和结果。
- `research_backend/pailie5/scientific_questions_v375.py`：科学问题及跟进规则。
- `research_backend/pailie5/scientific_runtime_v375.py`：受控调度和恢复。
- `research_backend/research_scientific_v375.py`：独立命令行。
- `research_backend/tests/test_scientific_questions_v375.py`：新增10项定向测试。

本地沙箱可运行批次，但不会在用户电脑或云端无限后台运行。运行中所有知识是探索性假设，不对外声称数学/彩票预测优势。
