# PL5 V1.9 自主能力发现、创造与协同研究版

**核心定位**：基于V1.8算法能力网络（AAN），增加目标驱动的能力缺口诊断、安全数学表达式创造、全10万号码跨实现核对、特征等价查重、历史前序回放和定时科研闭环。所有新算法仅限科研用途；**没有证据表明可提高排列五中奖概率**。

## 本版新增内容

- 四个自动研究方向：跨位置交互、模运算结构、时序几何、混合特征。每天6小时轮换目标，由脚本根据时间选择；研究方向、单轮提案上限可自行修改。
- **能力缺口规划**：为所选目标列出需要的指标、模式、过滤、实验验证能力；可通过`plan`查询。当前是有限能力目录的规划，不是开放世界语义推理。
- **声明式算法创造**：使用由`sum/span/odd/distinct/position/constant`原子能力与`add/sub/mul/min/max/abs/mod`组成的有界JSON运算树。限制深度和节点数，禁止任意Python源码、动态执行、网络指令和外部脚本。
- **独立算法复现**：NumPy与纯Python完全不同的实现计算整个00000—99999空间，逐号核对；同时计算指标分区签名，识别输出分组完全相同（即使值换了名字）的算法。
- **算法能力登记**：工程计算通过的新指标、模式和反延续过滤器各有独立UACP能力说明书和有向依赖；登记为`research`，未自动进入证据约束模式。
- **科研实验留痕**：SQLite保存原生数学表达式、算法来源、验证记录、源码可复核逻辑和历史探索回放。可使用官方归档的历史开奖，但回测不等于未来预测。
- **Web看板**：五序React工作台增加“自主能力创造实验室”只读卡片，展示新增指标、关联过滤器及验证状态。后端仍只监听127.0.0.1。

## 系统结构

```text
D:\pl5\
├── frontend\                GitHub五序原版 + 受审查增量面板
├── research_backend_v19\   原V1.8全部模块 + 新能力研究模块
├── runtime\
│   └── algorithm_abilities_v19.sqlite
├── data\official_archive_v17\
└── reports\v19\
```

本压缩包**不包含完整GitHub原版仓库**；安装器在必要时克隆`meilin2026dh/pl5`并固定已审查提交`9eb9ec5...`。已有`frontend`不会自动`git pull`/`reset`。安装器先检查前端源码和冲突，然后备份并增量安装，不覆盖用户改动。

## Windows部署

要求：D盘、Git、Python3.12、uv、Node.js24、pnpm11。解压后运行`install_to_D_v19.bat`。之后在PowerShell中：

```powershell
powershell -ExecutionPolicy Bypass -File .\验证_V19.ps1
powershell -ExecutionPolicy Bypass -File .\启动_V19_科研后端.ps1
```

另开PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\启动_V19_五序前端.ps1
```

浏览器访问 `http://127.0.0.1:5173/workbench`，可看到能力网络、能力创造研究成果。旧版`D:\pl5`数据及其他后端目录保留。

## 手动科研操作

```powershell
cd D:\pl5\research_backend_v19
$DB='D:\pl5\runtime\algorithm_abilities_v19.sqlite'
uv run python capability_cli_v18.py --db $DB bootstrap
uv run python ability_cli_v19.py --db $DB plan --goal cross_position
uv run python ability_cli_v19.py --db $DB research --goal cross_position --limit 3 --cycle-key first-run
uv run python ability_cli_v19.py --db $DB status
```

允许目标：`cross_position`、`modular_structure`、`sequential_geometry`、`hybrid_features`。同一`--cycle-key`及其配置仅运行一次，改动配置会被拒绝，以免事后重复实验。

**长期自动运行需显式启用**（先停用旧版本同类任务）：

```powershell
powershell -ExecutionPolicy Bypass -File .\启用_V19_定时科研.ps1
```

默认每天00:10/06:10/12:10/18:10在**开机且Windows允许**时运行；四个研究方向轮换，既执行旧版论文检索和官方数据归档，又运行本版有界算法研究。若官方归档可用且已验证，才在其基础上做探索性前序回测。旧任务存在时新任务拒绝重复注册。关闭后台用`停止_V19_定时科研.ps1`。不自动投注、不调用付费模型、不自动批准研究规则。

## 重要技术与科学边界

1. 本版算法创造是**受限数学语法内的自动构造**，并非完全开放式创造/忠实复现任意论文。外部未审查代码不能执行，未来若扩展任意Python需要独立容器沙箱，不能把`eval`或只靠AST检查当成沙箱。
2. 新算法的“双实现一致”只证明工程计算可重复，不证明其预测有效；等价类签名只证明全10万空间上指标分区一致，不足以证明统计方法等价。
3. 历史回测严格只读取目标开奖之前的数据；但动态试验、反复选模可能造成事后选择偏差。历史实验不被当成未见的独立检验。
4. 使用10万号码排序/输出100注在工程上可行；公平开奖前提下每期100注命中概率0.1%，连续10期至少一次约0.9955%。
5. 实际Windows前端构建、长期任务计划和官网联机验收尚未在本环境完成。离线演示使用的是**合成文献夹具**，并非真实论文验证。

## 文件说明

- `research_backend/pailie5/ability_lab_v19.py`：核心算法研究与能力缺口接口
- `research_backend/ability_cli_v19.py`：研究规划/生长/状态命令行
- `research_backend/research_v19.py`：衔接V1.7监督工作流及V1.9算法科研
- `research_backend/integration_server.py`：只读`/api/esse/ability-lab`接口
- `github_overlay/src/components/AbilityLabV19.tsx`：五序增量看板
- `integration_tests/upgrade_github_overlay_v19.py`：受保护的前端增量升级器
- `research_backend/tests/test_ability_lab_v19.py`：新算法安全、去重、互操作测试
- `V19_技术设计与验收报告.md`：实际测试、开放问题及下一阶段任务
