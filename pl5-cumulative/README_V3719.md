# PL5 V3.7.19 — 自主科研验证引擎（第一阶段）

本版在 `PL5_V3718_CI_Fix_Full.zip` 的 2,592 文件基础上无损增量扩展，保留所有旧算法与科研资料。新增统一回溯验证协议与三条独立技术路线的合成工程检查。

## 运行环境

Python 3.12+，在项目根目录执行：

```bash
python -m pip install -e './research_backend' pytest
python -m pytest -q research_backend/tests/test_research_validation_v3719.py
python research_backend/research_v3719.py --demo --demo-n 60 --warmup 40 --test-size 10 --top-k 100 --output runs/v3719/synthetic_audit.json
```

Windows PowerShell 使用相同命令，安装时可改用 `python -m pip install -e .\research_backend pytest`。

真实历史 CSV（需 `period,number` 2 列，期号递增、号码 5 位数字）：

```bash
python research_backend/research_v3719.py --csv path/to/draws.csv --warmup 40 --test-size 20 --top-k 100 --output runs/v3719/historical_audit.json
```

输出使用独占文件创建；同名证据已经存在时拒绝覆盖。无联网、投注和自动下注功能。

## 研究结构

- **统一预测对照**：`random`、`positional`、`pairwise`、`ensemble`、`heuristic_rank`（复用 V3.7.18 共享评分内核）。每一期只使用更早历史，生成完整候选集并计算 SHA256，然后才读取开奖目标；记录每期训练摘要、候选摘要、命中情况、Wilson 区间和单侧精确二项检验。对本轮多模型做 Bonferroni 校正。
- **独立非预测技术检验**：NCA 进行 50/30 时序拆分的合成数据关联拟合与测试；数学语言对 10x10 运算表进行遮蔽拟合和未观测格比较；GA-CS 与随机搜索使用同一冻结约束和同一 48 次评价预算。其评价指标不允许混进彩票命中率。
- **来源与科研等级**：报告标明 `synthetic_fair_iid` 或 `unverified_historical_csv`。本版只达到 `RETROSPECTIVE_WALK_FORWARD_ONLY`，不宣称开奖前封存，不宣称已找到真实预测优势。

## 局限与下一步

1. 目前未核验中国体育彩票的独立官方历史数据来源；历史 CSV 只能视为未验证来源。后续增加签名采集、公告时间戳及来源交叉校验。
2. 本版只修复了单轮候选族的 Bonferroni 多重比较，不能修复反复挑选同一测试区间或版本之间的试验选择偏差。下一阶段需要冻结一份从未用于开发的独立测试集，并开展真实开奖前候选封存。
3. NCA、算子发现及 GA-CS 是各自不同的研究问题，合成工程测试只能说明功能可调用，不能证明彩票预测优势。数学语言旧接口会同时返回持出格结果，**此合成试验不是外部盲测**，后续需改成训练与评测进程隔离。
4. 本版没有对现有 NCA、算子进化、GA-CS 的候选进行“预测胜率”统一排名，这需要先制定符合各算法输入假设、时间可用性与评价目标的转换契约。
5. 验收只覆盖当前运行环境，不等于 Windows `D:\pl5` 实机部署已完成。

工程任务优先级：独立数据验真 → 盲测封存 → 四路线预注册协议 → 真实端到端性能和漂移评估。

## 第二阶段：双源核验与前向封存（V3.7.19 Phase II）

本次新增本地封存包，继续保留全部第一阶段源码和历史累计归档。使用入口 `research_backend/research_prospective_v3719.py`，支持 `crosscheck`、`register`、`seal`、`settle`、`verify`。具体中文步骤见 `docs/v3719/PHASE2_GUIDE.md`，实测源码见 `research_backend/tests/test_prospective_validation_v3719.py`。公开期号交叉抽查记录见 `docs/v3719/PHASE2_REAL_SOURCE_SPOTCHECK.json`。

只有经过**独立第三方的开奖前时间证明**，才可能把本地 SHA256 封存升级为经过外部验证的前向证据。当前仅实现本地流程，不提供开奖前独立证明；不含任何真实彩票投注或预测盈利承诺。

## 第三阶段：真实官方数据摘录交叉核验与26295期公开摘要承诺

提供51期江苏/20期甘肃开奖记录转录，20期匹配；40期训练+11期历史滚动回测，五策略均0/11命中。于2026-11-05北京时间07:18:41公开26295期候选集摘要至GitHub草稿PR #4，详细说明见 `docs/v3719/PHASE3_GUIDE.md`。RFC3161独立时间戳回执未取得，不能据此宣称预测优势。
