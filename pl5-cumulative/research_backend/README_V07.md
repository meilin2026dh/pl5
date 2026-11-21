# PL5 V0.7 — 论文适配、指标创新筛选与长期前向验证

> **用途**：排列五自主科研的可复现性工程研究，不是彩票投注或中奖保证。保留V0.6全部功能；V0.7仅增量强化科研流程。

## 新能力及其准确边界

| 能力 | 已实现 | 不应声称 |
|---|---|---|
| 论文→研究协议 | 从已导入PDF全文/文本/摘要生成可审查的假设和复现步骤，保存论文ID、来源和摘要/fulltext状态 | 不能声称已忠实复现任意论文数学公式；摘要不能等同全文 |
| 指标自主生长 | 受限DSL生成新指标、在10万注空间计算签名、熵、状态数、相关性，与已有指标去重；有限搜索预算 | 指标有新意不等于有预测力；所有公式均安全解释、不得直接执行网页代码 |
| 审计评估 | 复用V0.6 NumPy与纯Python独立计算、逐期开发回测和公平随机对照 | 多重搜索后开发集p值不是独立预测证据 |
| 预注册、结算 | 检查目标期不在历史文件中、登记1–100注不可覆盖候选、哈希复核、开奖后增量结算 | 本地时间戳无法证明候选确在开奖前发布，也无法自动核实官方数据真伪 |
| 统计审计 | 不同K的精确公平基线、固定范围泊松二项尾概率、定额似然比混合e-process、非重叠10条记录统计，存在缺口时阻止跳期挑选 | e-value只有全部预注册且独立公平基线下才成立；多策略监控须额外控制误差 |
| 定时科研 | 原有定时抓取与研究后，附加每轮最多2篇、每篇2条的非冗余公式筛选 | 不能自动晋升正式过滤策略、自动投注，也不会自动启用Windows任务 |

## 安装与升级

1. 将本版本完整压缩包解压，双击 `install_to_D_v07.bat`。
2. 安装脚本限定目标为 `D:\pl5`，升级前备份被覆盖的程序，保持 `data/runtime/archive/research_reports/.venv` 目录不变。
3. 在Windows PowerShell执行：

```powershell
cd D:\pl5
uv sync --python 3.12 --extra agent --extra fulltext --group dev
uv run pytest -q
uv run streamlit run phase2_app.py
```

网页侧栏新增：`07 论文复现与前向验证`。

## 命令行示例

```powershell
# 先用V0.6导入本地PDF或txt
uv run python research_v06.py import --file data\paper.txt --key paper01 --title "研究材料"

# 抽取可审查的研究假设（不宣称忠实复现原论文）
uv run python research_v07.py paper-plan --key paper01

# 自动发掘非冗余公式：公式可注册为研究候选，但不自动加入正式预测/过滤
uv run python research_v07.py discover --key paper01 --limit 3

# 查看算法指纹和人工审批状态
uv run python research_v06.py status

# 在开发集对具体算法进行两路复现、零假设对照和审计
uv run python research_v07.py audit --fingerprint 算法指纹 --csv data\official_history.csv --official-source "official:人工逐期核验体彩公告" --k 100

# 只有人工审批进入research_approved的算法才有资格参与实验排名
# 必须在目标期开奖前运行，目标期不得存在于输入CSV
uv run python research_v07.py freeze --csv data\official_history.csv --official-source "official:人工逐期核验体彩公告" --target-period 2026310 --k 100

# 后续向CSV增添真实开奖结果，再结算封存记录
uv run python research_v07.py settle --csv data\official_history.csv --official-source "official:人工逐期核验体彩公告"
uv run python research_v07.py forward-report
```

注意 `--target-period` 仅为示意，使用时应替换为真正尚未开奖且大于当前最新期号的期号。数据保留 `period,number` CSV列，号码必须五位含前导零。 `--official-source` 是来源声明**而非程序独立验证**。

如果此前已显式启用V0.5/V0.6定时任务，该任务下次运行会自动采用升级后的 `定时科研_运行.ps1` 增加V0.7筛选。此前从未启用的机器不会自行启用。可手动执行 `启用_定时科研.ps1` 注册任务。只有电脑开机、用户环境及网络可用时任务才有机会运行；会有网络限流或失败。

## 新增代码

- `autoresearch/novelty_v07.py`：指标空间全量签名、熵、相关与冗余筛查
- `autoresearch/paper_protocol_v07.py`：论文方法迁移研究卡及独立复现计划
- `autoresearch/forward_v07.py`：预注册审计、逐期证据及缺口控制
- `research_v07.py`：CLI命令
- `pages/07_论文复现与前向验证.py`：Streamlit页面
- `tests/test_autoresearch_v07.py`：单元及端到端测试

## 100注/10期的数学边界

公平开奖下，任何开奖号码生成前固定的100注集合，每期准确命中概率均为 `100 / 100000 = 0.001`。若连续10期选择100注、开奖相互独立，至少一次命中为 `1 - 0.999^10 ≈ 0.9955%`。从“历史模式少见”推断“下期模式不该出现”是未经验证的赌徒谬误。系统可以模拟、筛查、证伪这种假设，但不能把排名分数直接称为真实概率。

## 安全及监管边界

- 不接受网页/PDF文字作为系统指令，不对从网上发现的Python源码进行直接执行。
- 保持个人密钥由环境变量管理；默认不自动调用付费模型。
- 研究知识库准入与预测应用准入分离。
- SHA256和SQLite触发器有助于本地审计，但无第三方可信时间证明，不能作为开奖前独立第三方证据。
- 算法持续提出新方案≠持续获得预测优势。若没有稳定的系统性偏差，合理结论可能始终是“未发现优势”。
