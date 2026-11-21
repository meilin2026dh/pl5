# PL5 V1.1 — ESSE 可逆解空间雕塑引擎

## 本次新增

在V1.0的基础上新增 `pailie5/sculpting.py`、`sculpt_cli.py`、`pages/11_可逆解空间雕塑工作台.py` 与单元测试，**保留所有V1.0算法模块和原有工作台**。

**目标**：把每条基础/时序/跨空间规则视为一把可撤销的刀，评估交集、边际删除、重复过滤、独有贡献，并在全10万号空间下生成可审计的排序和100注以内候选集。

### 实现能力

1. **无损可逆**：不物理删除号码；每次根据原始10万位集合和当前规则重新计算。支持开关、调序、撤销、重做、手动恢复/保护具体号码（五位字符串）。被保护的号码会优先进入最终K注名单；当保护号码数大于K时拒绝执行。
2. **两种边际贡献**：`newly_removed` 是该顺序下新增剔除数；`unique_recoverable` 是禁用一把刀时真正能恢复的唯一排除数，与顺序无关。未把重复切割错算为新增贡献。
3. **路径建议**：按当期新增排除数量贪心建议刀具顺序，**只优化计算/展示路径，不改善中奖概率**；相同刀具集合的交集与顺序无关。
4. **全空间偏好排名**：每个号码的规则惩罚及未校准权重；同组规则取最大权重，避免相同指标重复累加；同分用固定种子打散；完整10万注持续可审计。
5. **配额修复**：若硬过滤后不足K注，则明确将惩罚最低的过滤号码补回，标注 `restored_for_quota`；在任何情况下最终K注恰好K个不重复号码。若未过滤至K注以下，优先从硬保留号码中评分排序。
6. **前向滚动探索回测**：每一期仅使用开奖前的历史重建刀具，报告Top-K命中与公平随机基线；该历史回测不是独立封存验证。
7. **证据门禁**：支持 `mode='strict'`，只有通过独立审计系统传入 `approved_keys` 的刀具才参与计算；不能靠刀具自称 `evidence='verified'` 绕过。当前UI不提供导入审计签名，默认在严格模式下全部阻断（保守行为）。

### 运行条件

Windows 11，Python 3.12，uv；与V1.0同样的依赖。无模型API Key即可离线使用。实际读取真实数据前，应核对是否来自中国体彩网官方公告；系统不能仅凭CSV判断来源真实性。

### 安装（已有D:\pl5）

1. **先备份** `D:\pl5` 的重要数据（尤其 `data`、`runtime`、自定义配置）。
2. 解压完整包到任意文件夹；双击 `install_to_D_v11.bat`。
3. 安装脚本在替换程序文件前做SHA256校验，备份同名旧文件；不覆盖 `data`、`runtime`、`.venv`、用户配置；失败时尽力回滚。
4. 在PowerShell运行：

```powershell
cd D:\pl5
uv sync --python 3.12 --extra agent --extra fulltext --group dev
uv run pytest -q
uv run streamlit run phase2_app.py
```

左侧选择 **11 可逆解空间雕塑工作台**。

**离线CLI演示**（不会连接互联网，也不会下单投注）：

```powershell
uv run python sculpt_cli.py --k 100 --sum-max 25 --out runtime\esse_v11
```

**官方CSV**：

```powershell
uv run python sculpt_cli.py --csv data\official_verified.csv --k 100 --backtest 10 --out runtime\esse_v11_official
```

输出 `top_k.csv`（K注）、`all_100000.csv`（全量评分）和 `report.json`（逐刀审计、数据指纹及可选探索性回测）。

### 编程接口

```python
from pailie5.pattern_rules import Configuration
from pailie5.basic_filters import BasicConstraint
from pailie5.sculpting import knives_from_history, SculptSession

history = ['00110', '12345', '23456', '78901', '54321']
cfg = Configuration(indicators=('sum','span'), windows=(3,4))
knives, defaults = knives_from_history(history, cfg, [BasicConstraint('sum',maximum=25)])
s = SculptSession(knives,enabled=defaults)
sculpt = s.sculpt()        # 逐刀集合审计
report = s.counterfactual()  # 每把刀单独撤销时真实恢复量
s.set_enabled(next(iter(defaults)), False) if defaults else None
s.undo()                   # 恢复上一步操作
s.protect('00128')         # 用户指定保护号码
ranked, metadata = s.rank(k=100)
```

### 数学解释（重要）

- 公平、独立、均匀开奖时，每期任意一个具体号码的条件概率是 **1/100000**。任何根据历史数据自适应确定的K注集合，当期命中概率仍是 **K/100000**。
- `preference_weight_uncalibrated` 是从用户规则惩罚归一化得到的启发式权重，**不是已验证的真实中奖概率**。
- 100注在10期至少中一次的公平随机基线是 `1 - (1 - 100/100000)**10` ≈ **0.9955%**。
- 自动发现更多规则不代表多出了信息。要想声称超越随机基线，必须进行事先固定、独立的样本外或未来开奖结果验证，并修正多重测试及选择偏差。

### 当前尚未完成

- V1.1自身没有创造通用研究论文算法或自动签署验证凭证；沿用V1.0原有科研模块。
- 本版本的`strict`审批入口为Python API，未与V0.9的独立审计数据库签名连通；UI默认拒绝任何未经核准的刀具。
- 当前运行环境执行了Python自动化测试与CLI端到端演示，但未对用户Windows D盘、Docker或长期任务做现场验收。
