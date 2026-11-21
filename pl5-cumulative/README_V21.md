# PL5 V2.1 — 多智能体协同科研与独立证伪委员会

在 **V2.0完整源码** 基础上做增量研发，不替换 GitHub「五序」过滤逻辑，保留官方开奖归档、AAN能力网络、ESSE可逆雕塑、算法注册、论文引用锚点、Docker隔离实验以及既有数据表。

## V2.1增加了什么

新增`autoresearch/council_v21.py`持久化科研委员会。每个方法卡可形成一项研究任务，由八个明确角色阶段协同：

1. 文献研究员：锚定文献SHA、引用、页码/公式位置（可能待核验）；
2. 假设设计员：提出可证伪的实验研究假设、数学前提与零假设；
3. 能力网络规划员：识别缺失的算法接口、独立参考实现及验证工具；
4. 主算法工程员：登记符合安全语法约束的Python实现；
5. 参考算法工程员：登记结构不同的第二份实现；
6. 怀疑论审计员：提出数据泄漏、随机对照、多重检验、边界条件等反例测试清单；
7. 隔离实验员：**仅显式授权后**调用V2.0 Docker沙箱做双实现、重复执行及历史探索性对照；
8. 科学准入员：输出候选评审结果，**没有自动正式发布权限**。

这些是**独立职责、代码和审计产物**，不意味着8个大型语言模型正在并行运行。默认定时任务只能进行**方法卡→角色计划→能力缺口**，无法无人值守执行外部算法或真实论文的忠实复现。主、参考源码需要提交（人工或未来明确授权的大模型工程流程）；结构不同也不证明实现真正独立。

## Windows部署

1. 备份原有`D:\pl5`，解压本包；
2. 执行`install_to_D_v21.bat`（使用固定的GitHub基础commit克隆/复用前端，增量补丁先检查已有修改）；
3. 运行`验证_V21.ps1`（Python测试、前端依赖/TypeScript检查、生产构建须在Windows本机完成）；
4. 用`启动_V21_科研后端.ps1`、`启动_V21_五序前端.ps1`开启两个服务；
5. 进入`http://127.0.0.1:5173/workbench`，查看**多角色科研协同委员会**只读面板。

安装目标是`D:\pl5\research_backend_v21`，数据复用`D:\pl5\runtime\autoresearch.sqlite`。不自动删除旧版本、不运行付费模型、不执行陌生代码、不购买彩票。首次部署需要Git、Node.js24、pnpm11、Python3.12及uv。

## CLI科研流程

```powershell
cd D:\pl5\research_backend_v21
$DB='D:\pl5\runtime\autoresearch.sqlite'

# 若尚无论文方法卡，请按V2.0指南先导入论文并创建方法卡
uv run --no-sync python research_v20.py --db $DB status

# 对已有方法卡自动生成最多3个新研究协同计划（离线无付费）
uv run --no-sync python research_v21.py --db $DB auto-plan --limit 3
uv run --no-sync python research_v21.py --db $DB status

# 或使用一个已经创建的V2.0 blueprint ID新建定制研究项目
uv run --no-sync python research_v21.py --db $DB create --blueprint <BLUEPRINT_ID> --goal '核验这一方法的输入边界和可重复性' --budget 100 --periods 8
uv run --no-sync python research_v21.py --db $DB plan --project <PROJECT_ID>

# 各工程角色独立提交源码，不会在宿主Python执行
uv run --no-sync python research_v21.py --db $DB submit-code --project <PROJECT_ID> --role primary --file D:\papers\primary.py
uv run --no-sync python research_v21.py --db $DB submit-code --project <PROJECT_ID> --role reference --file D:\papers\reference.py
uv run --no-sync python research_v21.py --db $DB red-team --project <PROJECT_ID>

# 需要人工核查输入CSV和Docker安全配置后，显式批准容器实验
uv run --no-sync python research_v21.py --db $DB audit --project <PROJECT_ID> --csv D:\pl5\data\official_history.csv --allow-docker
uv run --no-sync python research_v21.py --db $DB decision --project <PROJECT_ID>
uv run --no-sync python research_v21.py --db $DB state --project <PROJECT_ID>
```

`red-team`在当前版本生成**可审查的反例检查计划**，并不假装已经独立执行全部反例试验。`audit`复用V2.0的Docker沙箱功能，不允许缺Docker时在主机回退运行。

## 长期科研

确认并停用旧版科研计划任务后，在Windows执行`启用_V21_定时科研.ps1`。默认每天00:10/06:10/12:10/18:10执行：原V1.9论文检索、官方数据归档、受限AAN创新；V2.0文献方法卡创建；V2.1协同研究计划创建。每轮最多`Limit`条新增计划，已存在项目按内容指纹去重。

**不会**通过此计划自动运行外部Python、付费模型、人工审查或自动发布到ESSE。仅在Windows允许任务执行并联网时运行；不是云端常驻服务。停止使用`停止_V21_定时科研.ps1`。

## 版本与可信性边界

- V2.1状态由SQLite不可变项目及事件记录衍生，每个研究产物具有SHA256与前一事件摘要连接；但本地SQLite与哈希不构成第三方时间见证。
- 文献/算法/结论可以证伪、审计、版本化；新的研究假设必须新开项目，不得涂改既有研究证据。
- 两份源码SHA或AST不同，仅说明代码文本/结构有差异；Top-K一致只说明该输出层面的工程复现，不证明完整论文复现。
- 历史回测是已见的探索性样本；“算法数量增长”与“提高真实未来命中率”是不同指标。
- 任何开奖前锁定的100注，在独立均匀开奖假设下单期命中概率仍是0.1%，10期内至少中一次约0.9955%。
