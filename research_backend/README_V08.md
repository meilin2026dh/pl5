# PL5 V0.8 — 开放式Python算法科研智能体

V0.8是对既有V0.7的**增量升级**：现有基础过滤、时序模式反延续、跨空间映射、算法竞争、论文全文接入、前向验证都继续保留。

> **严格限制**：这是一套算法研究实验系统，而非已验证的彩票预测工具。它能产生、审查与尝试证伪新算法，但不能把“随机中少见的模式”误认为“下一期必然更少见”。公平开奖条件下任何预先确定的100注集合单期命中概率始终为0.1%。

## 本次新增

1. 论文启发的**开放Python算法提案**：可离线提出两类基线研究模型；可在用户显式授权时，使用大模型从已导入全文/摘要提出新Python研究代码；亦支持人工提交代码。模型生成能力有边界，**不保证忠实复现任何论文**。
2. **代码审查与出处登记**：静态AST审查；只接受 `score_batch(history, candidates)` 接口；SHA256代码指纹、来源、实验假设及文献链接入SQLite。发现同一代码时去重并保留关联来源。
3. **隔离执行**：仅允许Docker Desktop/可信Docker引擎以无网络、只读文件系统、无额外Linux能力、非root身份、内存/CPU/进程/超时限制执行。没有Docker则拒绝运行，**不会回退到本机运行外部Python代码**。Docker是风险缓解，不提供绝对隔离保证。
4. **两次独立容器重复执行 + 逐期开发回测**：同一输入连续运行两次，要求排名完全一致；每个待验证期只使用该期之前的历史，计算完整10万候选的Top-K及公平开奖基线。注意这是**两次可重复运行，不是两份独立算法实现**。
5. **研究证据登记**：同一算法+数据摘要不自动重复审计。所有结果保留“development only / 未证实预测增益”，绝不自动提升到正式选号模型。
6. **定时自动提案**：现有每6小时扫描任务会追加 `research_v08.py auto-propose`，但仅生成代码候选，不执行；默认完全免费离线。只有同时设置 `PL5_ENABLE_PAID_PYTHON_CODE=1`、`PL5_ENABLE_PAID_LLM=1` 和 `OPENAI_API_KEY` 才允许定时调用付费模型生成代码，并限制每轮最多2篇文献。

## 本机环境

- Windows 10/11、Python 3.12、`uv`，若要测试*新生成的Python代码*，还需要**已启动的Docker Desktop**（启用Linux容器）。
- 为运行安全，建议使用非管理员账户、隔离的计算机/虚拟机或受限Docker主机，不要挂载私人资料目录到容器。
- `OPENAI_API_KEY`只在明确使用模型生成算法时需要，不需要上传给PL5。
- 真实开奖CSV必须包含`period,number`，5位号码前导零不得丢失。软件仅记录来源声明，不负责核验官方公告。

## 升级部署

解压完整包，双击根目录`install_to_D_v08.bat`；升级脚本备份被覆盖代码到`D:\pl5_backups\backup_before_V08_*`，保留`D:\pl5\data`、`runtime`、`.venv`、`archive`与`research_reports`，不会自动启用计划任务。

PowerShell检查：

```powershell
cd D:\pl5
uv sync --python 3.12 --extra agent --extra fulltext --group dev
uv run pytest -q
uv run python research_v08.py status
uv run streamlit run phase2_app.py
```

在页面列表进入 **08 开放Python算法科研实验室**。

## 完整科研操作示例

```powershell
# ① 首先导入论文文本（V0.6已有能力）
uv run python research_v06.py import --file examples\v06_paper_demo.txt --key demo-paper-08 --title "示例研究资料"

# ② 从该文献提出两类Python研究算法（不会运行）
uv run python research_v08.py propose-offline --document demo-paper-08

# ③ 查看代码哈希，然后审查源码
uv run python research_v08.py list
uv run python research_v08.py inspect --code-id <64位SHA256>

# ④ 使用Docker试验（需手动同意；每期严格遍历10万种号码）
uv run python research_v08.py audit --code-id <64位SHA256> --csv data\official_history.csv --k 100 --eval-size 8 --official-source "official:人工核验体彩公告" --allow-docker

# ⑤ 默认定时任务只做离线提案，不做代码执行/付费调用
uv run python research_v08.py auto-propose --max-documents 2

# ⑥ 付费模型独立提出算法：显式同意一次付费调用
uv run python research_v08.py propose-llm --document demo-paper-08 --confirm-paid
```

支持人工提交：`research_v08.py propose-file --document demo-paper-08 --source user_model.py --claim "这个算法仅用于随机序列假说检验，没有可靠预测增益证据"`。

## 已知技术边界与待完成验收

- 当前工作环境没有Docker引擎，因此**没有声称真实Docker隔离执行成功**；自动化测试使用模拟Docker命令/响应，真实Windows Docker需在机器上验收。
- 论文提案来源于文本理解和推导，不等于忠实复现作者的原算法；可信复现仍需要数学公式逐项比对和第三方独立实现。
- 开发回测是重复选择模型后的探索性证据，不用于断言超越随机；真正的预测验证必须在尚未开奖时预先封存、开奖后不可遗漏地结算，并控制不断新增模型引发的多重比较。
- 定时任务需要此前实际安装启用、电脑在线和联网；本部署包不会在你的D盘自行执行。
- Docker Desktop Linux容器内部安全选项需要在Windows实际验证；容器逃逸等风险仍须依靠可信宿主机、补丁与最小权限防御。

## 项目内新增文件

- `autoresearch/python_lab_v08.py`：代码静态审计、Docker强制沙箱、逐期实验及研究SQLite注册。
- `autoresearch/proposals_v08.py`：离线及可选LLM开放Python假设生成。
- `research_v08.py`：命令行科研流程。
- `pages/08_开放Python算法科研实验室.py`：Streamlit页面。
- `tests/test_autoresearch_v08.py`：安全、流程及独立重复执行单元测试。
