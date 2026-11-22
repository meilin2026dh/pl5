# PL5 V1.4 — 五序统一算法注册与科研规则准入

## 版本定位

这是在已经实现的V1.3 GitHub/ESSE跨语言桥接工程上，新增 **可审计的本地算法注册、独立测试记录、实验规则审批、撤销与按期限定的自动叠加**。不会擅自改变现有五序的基础/高级过滤行为。新增规则属于**实验性雕刻刀**，即使审批通过也不意味着获得可信的中奖彩票预测能力。

**重要**：本包的 `github_vendor` 附带此前从 `meilin2026dh/pl5` 读取并逐Git blob SHA验证的**4个原始源码模块**。完整React/TypeScript前端无法在本环境通过Git克隆；安装脚本会在 Windows 上尝试把真实完整GitHub代码克隆到 `D:\pl5\frontend`，如果已有该目录则直接复用而不执行pull/reset/checkout。没有把4个模块伪装成整个GitHub仓库。

## V1.4 增加什么

1. SQLite `algorithm_registry_v14.sqlite`：候选算法、10万位不可变掩码、来源域哈希、历史训练截止期、审查报告及事件链。
2. 本机命令行 `registry_v14_cli.py`：导入五序规则位图，评估历史留出数据，研究审批、注销和列举。
3. Python `run_bridge(request, registry=...)`：在原生严格AND位图完成全部校验后，才从本地数据库叠加**已批准、同来源大底、同截止期**的实验规则。
4. GitHub React界面新增可选实验规则ID输入与研究位图JSON导出；没有在网页中开放审核/批准API。
5. 原有源域保护、12500字节位图、逐位置比对、前导零、用户停止旧规则后的外部大底加载，均保留。
6. 登记和审批全程不执行第三方Python代码，不接入付费模型，也不自动下单。

## 正式操作

下载并解压发布ZIP，运行 `install_to_D_v14.bat`。安装路径：

```text
D:\pl5\
  frontend\                   GitHub完整源码（克隆或复用）
  research_backend_v14\       本次Python科研/ESSE后端
  github_vendor_v14\          4个核验过的GitHub原版模块
  runtime\algorithm_registry_v14.sqlite   本地算法证据库（首次使用时自动创建）
```

保留已有 `data`、`runtime`、旧版`research_backend_v13`及原有五序设置。安装器检测用户修改过的既有ESSE组件时拒绝覆盖。建议升级前自行备份D盘重要工程及浏览器方案JSON。

运行 `启动_V14_验证.ps1`，随后两个窗口分别启动 `启动_V14_科研后端.ps1` 和 `启动_V14_五序前端.ps1`。浏览器打开 `http://127.0.0.1:5173`。需要Python3.12、uv、Node24、pnpm11.25.0及Git（新克隆时）。

### 一次受审计的算法准入演示

1. 在五序工作台使用官方历史数据，选定基础过滤/历史规则，使用ESSE计算，并点击“导出规则位图研究请求JSON”，得到 `PL5_V14_research_mask_request.json`。
2. 计算你保留的**官方历史快照** SHA256，固定数据版本、来源域和训练截止日。下面只演示调用格式，不能把自报哈希当作官方验证。

```powershell
cd D:\pl5\research_backend_v14
$DB = 'D:\pl5\runtime\algorithm_registry_v14.sqlite'
uv run python registry_v14_cli.py --db $DB import-rule `
  --request 'C:\Users\Public\Downloads\PL5_V14_research_mask_request.json' `
  --rule-id 'your_rule_id' --creator 'research-agent' `
  --cutoff-date '2026-10-31' --source-ref 'github:meilin2026dh/pl5' `
  --data-sha256 '<SHA256-of-training-snapshot>'
```

3. 等有**晚于训练截止日且未被用于拟合的开奖**后，将至少10期官方历史记录保存为JSON数组。每条结构 `{"issue":"26291","date":"2026-11-01","number":"00123"}`（示例号码非真实开奖），执行：

```powershell
uv run python registry_v14_cli.py --db $DB audit <algorithm_id> --draws 'future-draws.json'
```

4. 由**非创建者**审阅实验记录与规则来源后明确批准**研究性使用**（CLI中的审核人只是本机记录标签，不是经过身份认证的签名）：

```powershell
uv run python registry_v14_cli.py --db $DB approve <algorithm_id> `
  --experiment-id <experiment_id> --reviewer 'reviewer' `
  --consent 'APPROVE_EXPERIMENTAL_NOT_PREDICTIVE'
```

5. 在五序工作台的 ESSE V1.4 面板输入该算法ID。**前端最新历史期号和注册时候的截止期号、号码来源域必须一致**，否则拒绝使用。新增一期后应基于新截止期重新生成并审核规则版本。
6. 规则失效后可 `revoke <algorithm_id> --reviewer 'reviewer' --reason '...'`；下一次运行必然拒绝使用已撤销算法。

通过 `uv run python registry_v14_cli.py --db $DB list` 查看注册表，通过 `verify-ledger` 检查事件链。

## 统计边界与限制

- 目前的“独立测试”是按**截止日期和不可变掩码**做防未来信息泄漏的机械检查，程序不能独立证实用户上传历史是否曾被研究人员查看、来源是否官方，也不能独立认证审批人真实身份。
- 审批通过只是允许作为**实验刀**进入ESSE。不存在自动认证的预测优势。完整评估必须继续使用真实、未被重复调参的开奖前封存前向实验与多重检验校正。
- 同一截止期的静态过滤刀不随新开奖自动更新；自动科研发现/生成能力沿用旧版，新的动态模型反复审批流程仍需后续实现。
- 一切排名/软分均是未经概率校准的探索性偏好，不是中奖概率。公平独立开奖下每期100注命中概率为0.1%，10期至少命中一次的随机基线约0.9955%。

## 工程验证

`research_backend/tests/test_algorithm_registry_v14.py` 验证版本指纹、不同来源域阻断、后验批准、审批撤销、事件链、历史截止期与不可信请求拒绝。`integration_tests/test_upgrade_v14.py` 验证全新安装与已有V1.3安全升级。请以当前ZIP中的 `V14_研发验收记录.md` 查阅实际测试执行结果，不能用过去版本的测试计数代替当前验收。
