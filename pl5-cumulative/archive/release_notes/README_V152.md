# PL5 V1.5.2 — 开奖前封存与逐刀证据台账

本版继承V1.5.1的五序React工作台、Python科研中枢、ESSE可逆雕塑、算法准入及竞争状态看板。在不修改远程GitHub主分支的前提下，新增**可运行的本地封存—结算—证据核验闭环**。

## 本版已做

1. 完整保留5位字符串与前导零；每期封存1—100注不同候选号。
2. **从五序ESSE面板导出的原生请求JSON重新运行Python桥接**，不直接相信一份随意填写的“计算成功”摘要。
3. 保存历史开奖快照SHA256、实际过滤截止期、研究代码版本、请求SHA256、逐刀过滤阶段、每刀完整10万位掩码及SHA256、最终号码集及其SHA256。注册规则仍须满足本机审批门槛。
4. SQLite封存行和结算行只增不改，事件链SHA256链接；禁止重复、回填，以及已存在于来源数据的目标期号。
5. 官方开奖更新后比较历史前缀是否改变，拒绝在数据冲突时批量结算；记录候选集是否命中、是哪把刀首次排除了开奖号码、哪些规则单独使用也会误删。
6. 报告只使用首个未结算记录之前的连续登记前缀，并比较固定预算下的公平随机基线。滚动10条为**已登记记录**，不可冒充连续10个实际开奖期。
7. 五序前端新增只读面板；状态数据仍经Node同源代理和回环Python服务获取。

## 安装到Windows D盘

下载解压后，双击 `install_to_D_v152.bat`，仅安装到新目录 `D:\pl5\research_backend_v152`。现有 `data`、`runtime`、旧后端及前端用户方案不会主动被删除。安装器复用已有GitHub五序前端；首次缺失时尝试克隆已经审查的提交。先运行 `验证_V152.ps1`，再分别运行 `启动_V152_科研后端.ps1`、`启动_V152_五序前端.ps1`。

## 每期使用步骤

1. 在五序 **历史走势** 页更新官方开奖缓存，检查来源和截止期。
2. 在 **ESSE雕塑工作台** 选好规则，运行跨语言雕塑，并点击“导出规则位图研究请求JSON”。**先不要把新一期真实开奖号录入候选请求**。
3. 在PowerShell中执行（请替换实际目标期号与文件路径）：

```powershell
cd D:\pl5\research_backend_v152
uv run python research_v152.py --db D:\pl5\runtime\sculpt_evidence_v152.sqlite seal `
  --cache D:\pl5\frontend\.cache\history.json `
  --request D:\Downloads\PL5_V14_research_mask_request.json `
  --target 26291 --source '中国体育彩票官方接口本机缓存' `
  --code-revision '本次实际使用的git提交或版本号'
```

若使用已审批的实验性算法ID，还需加 `--registry-db D:\pl5\runtime\algorithm_registry_v14.sqlite`。封存只能在目标期不出现在缓存且期号严格递增时进行。**实际期号要自己核对，26291仅为示例，不能拿历史已开奖期进行真正前向封存。**

4. 目标期开奖后，再在 **历史走势** 页面刷新官方结果，然后执行：

```powershell
uv run python research_v152.py --db D:\pl5\runtime\sculpt_evidence_v152.sqlite settle `
  --cache D:\pl5\frontend\.cache\history.json --source '中国体育彩票官方接口本机缓存'
uv run python research_v152.py --db D:\pl5\runtime\sculpt_evidence_v152.sqlite report
uv run python research_v152.py --db D:\pl5\runtime\sculpt_evidence_v152.sqlite verify
```

5. 返回五序工作台的“开奖前封存·逐刀证据台账”，点击刷新。

上述命令创建和更新的是**本地、按期封存的SQLite研究账本**，不进行自动购彩、自动审批或后台自动提交。

## 安全与统计边界

- 官方缓存的URL、时间和结构可供审计，但这些本地字段**不构成可信的官方数字签名**；本地时钟与SHA256也不构成可信第三方开奖前时间戳。
- 系统可验证规则在当时提供的数据下计算结果一致，但**不能证明用户未提前获知实际开奖号**。
- 规则压缩到100注是候选集大小限制，而不是概率成功证明。公平独立开奖下100注单期命中概率=0.1%，10期至少命中一次约0.9955%。
- 如果使用浏览器前端之外的自定义规则，必须先经过位图验证；未知类型可能只完成位图交集比对，并没有跨语言独立数学实现。
- 一旦前向试验开始，修改规则、模型或探索新策略，必须创建单独的研究系列，不能把事后选择的历史赢家冒充独立前向证据。
- 如果官方数据最新2000期窗口逐步滚动，导致早先的封存前缀已不在新缓存中，结算会拒绝执行。后续须引入完整官方历史持久归档，不建议绕过该检查。
- Windows实机、完整GitHub前端构建、实时官方网络接口、Docker和长期定时任务均未由当前环境实际验收。

## 主要文件

- `research_backend/pailie5/forward_sculpt_v152.py`：逐刀封存、结算、报告、完整性校验
- `research_backend/research_v152.py`：受控本地命令行
- `research_backend/status_v151.py`：增加只读前向状态字段（保持接口兼容）
- `github_overlay/src/components/ForwardEvidence.tsx`：前向证据看板
- `integration_tests/upgrade_github_overlay_v152.py`：安全升级脚本
- `research_backend/tests/test_forward_sculpt_v152.py`、`test_v152_cli.py`：功能/命令行测试

本版与早期V0.7基于研究公式的前向封存是**两套不同的证据记录**。V1.5.2针对GitHub ESSE的逐刀位图和候选名单，后续应在充分审计基础上考虑统一迁移账本；本版不会静默合并以前的记录。
