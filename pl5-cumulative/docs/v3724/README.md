# PL5 V3.7.24 — 受限组合语法发现与内部盲态测试

## 研究边界

本研究在10×10有限整数域内测试自动程序搜索。它能在单特征语法拟合失败时扩展为预定义的双特征组合操作（add/sub/mul/xor），**不是自主发明未知基础数学运算**。合成数据由本项目编写出题程序生成，**不是外部盲测**；没有验证排列五存在可预测信号。

## 新模块

- `research_backend/pailie5/grammar_discovery_v3724.py` — 明确限制的表达式DSL、固定2200程序评估预算、训练/验证/持出分离、SHA256承诺和只允许一次评估。
- `research_backend/research_grammar_v3724.py` — 分步的 `fit`、`freeze`、`evaluate`、`commit-holdout` 命令行。
- `research_backend/benchmark_grammar_v3724.py` — 48组×2种语法的开发期预注册合成实验；每臂总计105600次程序评估。
- `research_backend/tests/test_grammar_discovery_v3724.py` — 程序限制、平衡预算、避免泄漏、完整性检测、空白对照和重现性测试。
- `runs/v3724/benchmark/` — 协议、逐组出题样本、训练/冻结/测试证据和汇总。

## 安装与演示

在`research_backend`目录使用Python3.12+环境，安装本项目测试依赖：

```bash
python -m pip install -e '.[dev]'
python -m pytest -q tests/test_grammar_discovery_v3724.py
```

重现实验（**请选择新的空输出目录**，原目录通过只创建文件防止覆盖）：

```bash
python benchmark_grammar_v3724.py ../runs/v3724_replay
```

面向独立任务提供分步CLI（研究方在fit和freeze之前不得接触holdout文件，需由外部系统保障权限隔离）：

```bash
python research_grammar_v3724.py commit-holdout --holdout PRIVATE_holdout.json --nonce LONG_SETTER_NONCE
python research_grammar_v3724.py fit --train train.json --study trial/expanded --arm expanded --digest 64_HEX_COMMITMENT
python research_grammar_v3724.py freeze --validation validate.json --study trial/expanded
python research_grammar_v3724.py evaluate --holdout PRIVATE_holdout.json --study trial/expanded --nonce LONG_SETTER_NONCE
```

`PRIVATE_holdout.json`不应置于研究方可见的目录；以上命令由独立出题方/验证方分阶段执行。文件哈希不是第三方可信时间戳，也不是进程隔离。外部盲测：**尚未执行**。

## 限制

- 2200程序评估次数配平，但候选生成复杂度不同；不等于总CPU/GPU/能耗配平，不据此作全链路速度优势结论。
- 单特征基线包含相同前400个仿射候选，后1800个二次候选；新引擎则后1800个来自双特征运算。结果只对该基线成立。
- 训练集48、验证16、持出36。开发者知道所有合成家族，测试集不参与模型拟合和冻结选择。
- 零误差合成结果并不代表外部任务或彩票研究的预测优势。需要独立第三方出题、外部评审、预注册和真实前向检验。
- Windows D:\pl5部署与GitHub推送不属于本轮已完成测试。
