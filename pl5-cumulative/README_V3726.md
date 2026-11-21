# PL5 V3.7.26 — 条件结构归纳、配对CPU预算与盲测交接

**用途：科研实验，不用于购彩决策。预测优势：未建立。外部独立盲测：尚未进行。**

## 本轮新增

1. `research_backend/pailie5/gate_induction_v3726.py`：对预定义、有限的25类谓词候选进行训练数据拟合，支持输入相等、大小关系、和阈值、模同余条件门控；输出必须经过验证集冻结，测试集仅结算一次。此为有限域条件程序归纳，**不是新数学定律的发明**。
2. `research_backend/benchmark_gate_induction_v3726.py`：50组开发者编写的内部合成任务，3个独立算法+1个冻结选择组合，统一记录所有任务（含弃权），同机轮换运行顺序，报告实际`process_time`与25/50/100/250/500/1000毫秒门槛的有效成功数。
3. `research_backend/research_external_challenge_v3726.py`：公开挑战/私有答案两方交接和双算法评测；仅有外部出题身份核验、物理权限隔离、独立时间戳、签名及公开预注册后才可称为真正的外部盲测。
4. `research_backend/tests/test_gate_induction_v3726.py`：数学性质、验证/测试隔离、随机拒绝、反篡改、禁止重复结算及组合选择测试。

## 本次内部配对实验

共有10类合成函数×5个种子=50个任务，每个任务48格训练+16格验证+36格持出。总结果：V3.7.24成功5组，V3.7.25成功20组，V3.7.26成功30组，冻结组合成功35组。所有接受任务的持出测试错误0；**不能外推到任意未知数学结构或彩票开奖**。V3.7.26遇到三次交互结构仍可能弃权，这是新机制的已知边界，不能只报告改善案例。

计算预算不是“等候选次数”；不同算法一次程序评估与一次矩阵求解不能等价。当前仅用同机CPU时间门槛报告可比较的预算区间，**没有将运行时间截断强制设置为同一硬停止**，且不包含开发、源知识发明、能耗和外部挑战调度的全部成本。结论仅在上述条件下成立。

结果：`runs/v3726/internal_paired_final/{protocol.json,results.csv,summary.json}`，重跑结果在`runs/v3726/internal_paired_replay/`，详细说明在`docs/v3726/RESEARCH_REPORT.md`。

## 使用（在research_backend目录）

```bash
python -m pip install -e '.[dev]'
python -m pytest -q tests/test_gate_induction_v3726.py
python benchmark_gate_induction_v3726.py ../runs/v3726/new_local_benchmark
# 以下三个命令必须由独立的挑战提供方、求解方和评测方分别在隔离环境执行：
python research_external_challenge_v3726.py prepare --challenge challenge.json --public PUBLIC --private PRIVATE
python research_external_challenge_v3726.py solve --public PUBLIC/public_challenge.json --out SOLVER
python research_external_challenge_v3726.py grade --public PUBLIC/public_challenge.json --private PRIVATE/private_challenge.json --out SOLVER
```

**注意**：完整包里的`runs/v3726/handshake_demo/`是同机第一方示例，包含私有答案，因此不能用于证明外部盲测。新试验须使用独立出题者自行创建的任务与独立凭证。 

**尚未完成**：Windows `D:\pl5` 实机部署、GitHub代码推送、第三方外部盲测及真实彩票开奖长期前向优势验证。
