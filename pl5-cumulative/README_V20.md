# PL5 V2.0 — 论文方法驱动的开放式算法研究工厂

**定位**：沿用 V1.9 的 GitHub 五序工作台、AAN 能力网络、ESSE 过滤与 V1.7 定时科研，新增可以追溯到文献原文的研究方法卡、用户审阅/显式授权的大模型算法提案、容器隔离双实现对照、UACP 型能力说明书及只读网页面板。

> 所有自动发现的论文方法与算法均为**科研候选**。工程复现、历史表现和压缩到100注均不能证明有预测优势。公平独立开奖下，100注每期直选命中率仍为0.1%。

## 与 V1.9 的关系

- V1.9 有界数学表达式算法自动生长继续运行；V2.0 **不会取代**既有指标、时序反延续、跨空间映射和可逆ESSE。
- V1.7论文采集/官方开奖归档仍由原科研监督器负责。V2.0默认接收已有`autoresearch.sqlite`里的文献资料；每轮自动生成至多3份**待复核论文方法卡**。
- 只有用户显式启用付费LLM后，才可能从论文方法生成`score_batch(history,candidates)`的实验Python源码。非授权运行绝不做付费调用。
- 非白名单Python代码**只能在Docker容器中**执行；没有Docker就拒绝实验，不回退到主机Python。用户需要提供独立第二份实现，沙箱对照只能比较Top-K一致性，不能自动认证论文的忠实复现。
- V2.0外部Python能力**不加入可执行的AAN白名单**，只写入隔离的科研能力目录，禁止未经人工审核自动加入正式过滤。

## Windows安装

需要`D:`磁盘、Git、Python3.12/uv、Node.js24/pnpm11。解压后执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_to_D_v20.ps1
powershell -ExecutionPolicy Bypass -File D:\pl5\验证_V20.ps1
powershell -ExecutionPolicy Bypass -File D:\pl5\启动_V20_科研后端.ps1
```

另开终端启动前端：

```powershell
powershell -ExecutionPolicy Bypass -File D:\pl5\启动_V20_五序前端.ps1
```

浏览器进入 `http://127.0.0.1:5173/workbench`，可在“论文方法与能力创造中心”查看最新研究卡、原文依据、代码连接及复现状态。

目标目录 `D:\pl5\research_backend_v20`，前端继续使用`D:\pl5\frontend`。旧后端、`data`、`runtime`及实验记录不主动删除。首次克隆前端固定到此前检查的 GitHub commit `9eb9ec5...`；已有前端不自动拉取或重置。增量脚本先检查修改冲突并备份。

## 自动科研（需用户主动开启）

先关闭此前V1.7/V1.8/V1.9的同类科研任务，避免重复执行：

```powershell
powershell -ExecutionPolicy Bypass -File D:\pl5\启用_V20_定时科研.ps1
```

默认每天 `00:10 / 06:10 / 12:10 / 18:10`（Windows本机时间），在开机及Windows允许执行的情况下：

1. 继续原V1.9官方开奖同步、在线论文元数据发现、限定公式创新、实验记录；
2. 读取文献登记库中的最新成果；
3. 为尚未研究的文献创建含**逐字匹配原文摘录**的方法卡；
4. 将新方法卡纳入只读研究目录，等待人工审查及进一步创造算法。

默认不自动下载并执行GitHub上的陌生脚本、不自动批准规则、不自动开付费LLM、不自动选购彩票。

停止任务：`停止_V20_定时科研.ps1`。

## 手动研究真实论文

在 PowerShell 中进入 `D:\pl5\research_backend_v20`：

```powershell
$DB='D:\pl5\runtime\autoresearch.sqlite'

# 已下载真实论文 PDF / MD / TXT，明确标题与来源后导入
uv run python research_v20.py --db $DB ingest --file D:\papers\example.pdf --key paper-001 --title "原论文标题" --url "论文原始来源URL"

# 默认提取未审核的文献方法线索，不生成或执行Python源码
uv run python research_v20.py --db $DB auto-extract --limit 3

# 查看方法卡编号和来源
uv run python research_v20.py --db $DB status

# 可选：经过审阅的方法卡，用JSON schema提交
uv run python research_v20.py --db $DB extract --document paper-001 --blueprint-json D:\papers\verified_method.json

# 两份独立实现必须人工核实，且明确区分参考代码和主实现
uv run python research_v20.py --db $DB propose-code --blueprint <ID> --role primary --source D:\papers\primary.py
uv run python research_v20.py --db $DB propose-code --blueprint <ID> --role reference --source D:\papers\reference.py

# 研究阶段的Docker隔离配对实验；需要安装并启动Docker Desktop
uv run python research_v20.py --db $DB audit --blueprint <ID> --csv D:\pl5\data\official_history.csv --budget 100 --periods 8 --allow-docker
```

**大模型代码创造是可选功能**，使用`extract/propose-code --paid-llm --confirm-paid`并配置自己的API密钥后才会执行。LLM产出仍需原文核验、静态分析、独立实现与隔离实验。示例代码在`research_backend/examples/v20_*`，示例文献是**合成教学材料，不是真实论文**。

## 能力协议（科研目录）

每张方法卡包含版本、输入`history<five_digits> + candidates<five_digits>`、输出`ranking<five_digits>`、依赖的历史快照、沙箱、审计器、原文片段与哈希、两份代码哈希、实验记录、限制说明。它在内存和数据库中都被标记为`research_unverified`或`sandbox_compared_research_only`，不能直接注册为预测有效的正式刀具。

## 尚未实现及必须严格界定的事项

- **没有完全自主地复现任意论文的作者方法**。默认离线生成“研究线索”，由研究者检查公式和假设；大模型辅助实现属于迁移尝试。
- 双实现的代码SHA不同不保证真正独立；即使Top-K相同也不证明两个公式逐值一致，更不证明未来可预测。
- 历史对照是重复使用的探索性测试；尚未获得持续、锁定且经第三方时间见证的独立前向预测优势证据。
- 定时计划程序运行依赖你的Windows环境与网络。当前交付**没有直接安装到你的D盘或注册实际后台任务**。
- 生产完整GitHub前端由Windows安装脚本克隆或复用，ZIP不包含GitHub 275个文件；本地实验环境未完成Node24/pnpm11生产构建和Docker实机运行。
