# PL5 V3.7.27 — 强制时间预算与分权盲测协议

**研究性质**：仅支持合成数学程序的科研验证。**彩票预测优势尚未建立**。本版本没有完成真正的外部独立盲测。

## 本轮变化

- `research_backend/research_hard_budget_v3727.py`：在独立子进程内运行 V3.7.25 和 V3.7.26，各自设置同一**真实 wall-clock 强制截止**，超过上限直接终止；暂停或不完整的输出不允许评分。
- `research_backend/benchmark_hard_budget_v3727.py`：16个开发者设定的任务，两个固定时间预算，结果不只报告拟合成功，还报告全部失败、弃权、超时和负对照。
- `research_backend/resume_benchmark_v3727.py`：支持保留被中断实验原件后分段恢复，可重新收集完整结果；不把未完成实验当已完成。
- `research_backend/tests/test_hard_budget_v3727.py`：新增18项超时、防篡改、数据隔离、重复结算、样本分区测试。

## 协议安全边界

- 出题者在不同机器上运行 `research_open_grammar_v3725.py prepare`，将 `PRIVATE` 单独保管。求解者**只能**收到公开目录 `PUBLIC`。
- 求解者运行 `python research_hard_budget_v3727.py solve --public PUBLIC/public_challenge.json --out SOLVER --budget-ms 3000`。
- 评测者在求解冻结后运行 `python research_hard_budget_v3727.py grade --public PUBLIC/public_challenge.json --private PRIVATE/private_challenge.json --out SOLVER`。
- `sha256` 和文件存在性限制只能检测普通修改与重入，**不能证明操作者身份或阻止有文件系统权限的人读取私有答案**；需要独立方身份确认、权限隔离与外部签名时间戳，才能说完成外部盲测。

## 时间预算对照

在 Linux / Python 3.13 环境，16组内部合成任务×两预算：

|模型|800 ms / 任务|3000 ms / 任务|
|---|---:|---:|
|V3.7.25|0/16（16次超时）|6/16|
|V3.7.26|0/16（16次超时）|10/16|
|冻结组合|0/16|12/16|

组合算法按照两个模型分别运行计费，**总预算最高为6,000ms**，与单模型预算不同。3,000ms下接受的持出格无错误；四个负对照（两个噪声、两个复杂结构）均弃权。

**不计费项目**：研发、数学源知识搜索、出题方生成挑战和评测方结算。因此这里的硬预算是*求解工作进程从启动到冻结证据输出*，而不是整个自主科研全成本。

文件：`runs/v3727/internal_hard_budget/{protocol.json,results.csv,summary.json}`，逐任务保存在 `runs/v3727/internal_hard_budget/tasks/`；所有这些内部演示的私有答案随包归档，仅用于复现，**不可充当第三方盲测**。

尚未完成：GitHub 推送、Windows `D:\pl5` 部署、第三方出题和未来彩票开奖前向独立验证。
