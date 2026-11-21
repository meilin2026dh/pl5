# PL5 V3.7.6 — 科学实验方法自主设计（累计研究版）

## 已实现的能力

在 V3.7.5 科学问题库基础上，V3.7.6 增加了一个**受限、可审计的方法设计语言**：系统针对旧问题中的泛化失败，自动提出并执行「增加训练信息」「扩大数学表达式树上限」「增加计算预算」「输入坐标均衡采样」「跨任务族比较搜索引导策略」等实验干预。它不生成/执行任意 Python，不触碰真实下注，所有操作保持有界和可复现。

## 从原来12轮继续的研究记录

- `runs/autonomous_v375/`：原 V3.7.5 累计 12 轮，按字节保留。
- `runs/autonomous_v376/`：全新 8 轮方法对照，每轮都先锁定试验计划、随机种子、预算和20个测试坐标，再训练两组模型并冻结模型，然后计算同一个封存测试集上的成绩。
- 研究结果：首批方法未显示稳定泛化改进；已自主生成新问题 `Q-method_family_nonimprovement` 与 `Q-new_primitive_needed`。当预批准实验方法耗尽时，控制器安全停止，而不是继续重复相同实验。
- 这是对**人为设定的合成数字运算表**进行的探索性研究，不是彩票预测、不能证明数学原语发明能力或真实过滤优势。相同结构族换随机划分不等于获得独立的科学结论。

## Windows 本地复现实验

下载后解压至独立目录，准备 Python 3.12+ 和项目依赖：

```powershell
cd D:\pl5\research_backend
py -3.12 -m pip install -e .
py -3.12 -m pip install "pytest>=8,<10"
py -3.12 research_methods_v376.py --historical ..\runs\autonomous_v375 --output ..\runs\autonomous_v376_demo --studies 4 --budget 500 --seed 37681 --control-every 4
```

也可双击根目录 `RUN_V376_DEMO_ONCE.cmd`。它创建新的 `runs/autonomous_v376_demo`，不会覆盖压缩包附带的8轮证据。

若指定 `runs/autonomous_v376` 继续，则当前方法族的结构任务已基本耗尽、需要新数学原语研究；控制器会安全暂停并给出原因。该控制器不是无需照管的常驻后台服务，也不自动修改程序源码。

## 核心文件

- `research_backend/pailie5/scientific_methods_v376.py`：方法生成与选择、负对照调度。
- `research_backend/pailie5/scientific_runtime_v376.py`：冻结实验计划、训练、锁定模型、独立评价、记录研究问题。
- `research_backend/research_methods_v376.py`：有限轮次 CLI。
- `research_backend/tests/test_scientific_methods_v376.py`：自动化测试。
- `docs/v376/REPORT.md`、`docs/v376/VERIFICATION.json`：研究报告、真实验证结果。

**已知限制：** 不是开放式科研智能体，缺失数学新原语发明、实验假设自动生成任意可执行算法、实时市场数据接入、系统全天候服务及正式统计确证。所有结论都须经独立未来数据验证。
