# PL5 V3.7.29 — 独立数学任务盲测预注册与交接

**状态：PREPARATION / INTERNAL PROTOCOL SMOKE TEST。** 本文件不是第三方实验结果，也不表明已经完成 100 道未知任务的数学求解。

## 一、冻结研究对象

- 上一正式基线：main @ c0e38040ec5f389d6444e64b90e7adc42adfca62。
- 本阶段只增加盲测协议校验、统计、对抗测试和文档，不修改原 V3.7.25/26 数学求解内核。
- 冻结的独立方法：V3.7.25 环代数、V3.7.26 条件门控、两模型冻结组合。
- 在外部任务抵达前，必须另行封存完整的 Python 依赖锁、运行镜像/OS、机器规格、源码 Git SHA 和三方公钥指纹。仅对 pyproject.toml 求摘要不等于完整环境冻结。
- 本项目提供的 preregister 文件属于自声明。第三方未审核身份、未外部可信计时前，不算已完成科研级预注册。

## 二、独立出题（需要第三方实际执行）

请不参加模型研发/调参的出题方设计至少 100 道此前未知的有限域运算表任务。每道题共有 100 个输入坐标，其中 48 个训练坐标、16 个验证坐标、36 个隐藏评分坐标。至少 25 道真实无结构负对照。题目应包括旧算法可表达、跨结构迁移、旧语法难以表达及无可学习规律的任务。

独立出题方应在研发方无法访问的设备或权限域保留每题私有答案、随机盐、题族标签及生成规则。公开交付仅允许每题 V3.7.25 格式的训练/验证 JSON、持出承诺及其公开 SHA256 文件摘要。公开 manifest 的 tasks 数组应为恰好 100 项，每项仅含 task_id 和 public_sha256；不能公布任务类别、公式、答案、盐或生成器。第三方必须保存签名及外部可信时间记录。

## 三、公平计算预算与主要指标（事先固定）

| 方法 | 总预算 / 每题 | 约束 |
|---|---:|---|
| V3.7.25 独立模型 | 10000ms | 独立进程冷启动、包含导入训练冻结落盘 |
| V3.7.26 独立模型 | 10000ms | 同上 |
| V3.7.25 + V3.7.26 冻结组合 | 10000ms | 两个模型各最多5000ms，双臂总预算不超过10000ms |

不可将组合两个 5000ms 结果中的单臂成绩冒充另一次 10000ms 单模型对照。记录每次机器配置、依赖指纹、实际 wall clock、失败原因、超时、输出及可核验签名。计算资源、历史研发成本及出题人工作量另行统计，不得偷换全成本概念。

主终点为所有 36 隐藏格完全正确，且在预算内完成；任何错误、超时、失败、弃权或缺失计 0。分母始终为全部预注册任务。负对照报告错误接受次数，不得删除任何失败题。预选主比较是组合方法对 V3.7.26，双侧精确 McNemar 检验，附描述性 Wilson 95% 区间。题族相关性可能使普通配对显著性夸大，因此正式科学结论还须另行独立题族/聚类稳健复核。本工具不自动宣称科研发现成立。

## 四、软件接口

从 pl5-cumulative/research_backend 目录调用 research_blind_protocol_v3729.py。

1. 预注册：preregister --source-commit [40位冻结Git提交] --environment-sha256 [64位完整环境锁摘要] --out preregistration.json
2. 公共面板完整性：check-public --plan preregistration.json --manifest public-manifest.json --folder public --out panel-intake.json
3. 独立评分人在持出答案结算后出具 score-ledger.json 和 private-metadata.json（见下）。先使用 research_blind_ledger_v3729.py sign --plan preregistration.json --manifest public-manifest.json --ledger score-ledger.json --grader-private [评分方私钥] --grader-public [已登记的评分方公钥] --out signed-grade-ledger.json。这一步由评分方在独立受控环境操作，私钥绝不上传 GitHub。
4. 审计端使用 research_blind_ledger_v3729.py verify --plan preregistration.json --manifest public-manifest.json --ledger score-ledger.json --grader-public [核验过指纹的评分方公钥] --attestation signed-grade-ledger.json --out ledger-signature-check.json；签名证明该公钥签过这些字节，不证明其身份独立。
5. 最后运行 research_blind_protocol_v3729.py summarize --plan preregistration.json --manifest public-manifest.json --private-metadata private-metadata.json --ledger score-ledger.json --signed-ledger signed-grade-ledger.json --grader-public [核验过的评分方公钥] --out unverified-summary.json。命令行**强制验签后才能形成汇总**；账本还必须包含 preregistration_sha256 和 public_manifest_sha256，私有分类 ID 与公开任务逐项一致。

其中 score-ledger.json 必须包含 schema=pl5-v3729-score-ledger-1、solver_source_commit 及 results 数组。每条记录包含 task_id、arm、status、holdout_errors、holdout_cells、budget_ms、receipt_verified。receipt_verified=True 只是**独立审计完成后写入的结果字段**；本脚本不会自己验证那个字段代表的三方签名链或硬件时钟真实性。

private-metadata.json 的 schema=pl5-v3729-private-strata-1，categories 为 task_id -> structured / negative_control / out_of_grammar 的映射。此文件只能在求解冻结后由评分方提供，不应让求解端接触。

模块输出始终标注 external_blind_verified=false、trusted_timestamp_verified=false、lottery_predictive_advantage=NOT_ESTABLISHED；汇总报告新增 grade_ledger_signature_verified=true 只证明账本签名本身有效，不证明真实第三方或单题底层工人回执逐一外审。无论统计显著与否均不自动升级认证等级。

### 等总预算三角色执行适配器

新增 research_equibudget_v3729.py，不改 V3.7.25/26 求解算法：
- **出题方**：issue --public [公开题] --backend [冻结源码目录] --issuer-private [私钥] --issuer-public [公钥] --out [出题收据目录]。分别签发 10000ms 的单模型挑战与每臂 5000ms 的组合挑战；
- **求解方**：freeze --public [公开题] --backend [冻结源码目录] --attestations [出题收据目录] --issuer-public [出题公钥] --solver-private [求解私钥] --solver-public [求解公钥] --out [隔离求解目录]。分别完成 10 秒单臂对照和两臂各 5 秒的组合求解，两个结果都冻结完毕，才允许交付评分；
- **评分方**：grade --public [公开题] --private [私有题] --backend [冻结源码目录] --attestations [出题收据目录] --issuer-public [出题公钥] --solver-public [求解公钥] --grader-private [评分私钥] --grader-public [评分公钥] --out [已有隔离求解目录]。先核验两个冻结结果，再打开私有标签；输出三个同为 10000ms 总预算的成绩和单独的时间测量记录。

**适配器结果仍为内部/身份未核验**。即便单题三签名过程通过，也不能把本地时钟冒充可信硬件测量，不能用一台研发设备扮演三角色冒充独立盲测。

## 五、当前阶段通过与未通过的边界

已实现：
- 100份公开挑战的逐字节 SHA256 和字段校验，防止私有标签出现在公开 JSON；禁止重复任务、重复坐标、输入范围越界、目录符号链接逃逸。
- 全部题目计入分母，缺失按失败处理；负对照不少于25道；同预算结果核验。
- 预注册文件不能覆盖，冻结 commit 与环境摘要必须完整；统计提供 exact McNemar 和描述性区间。
- 针对内部合成公开面板和 Ed25519 签名账本运行 Windows/Linux Python 3.12 CI；新增独立单题等预算三角色试验适配器与内部回归测试。

仍未实现或未取得：第三方出题者的真实独立身份核验与私有答案独立托管，可信外部时序与硬件运行证明，100 道未知任务的真实求解和底层每题证据逐一第三方审计，跨题族稳健显著性，以及彩票未来开奖前的长期前向检验。这些缺失不能用模拟结果弥补。


## 六、整批任务证据审计（V3.7.29 新增）

`research_panel_evidence_v3729.py` 是评分端使用的**逐题签名收据核验与结果账本组装器**，不是一个能自动伪造外部出题人的生成器。正式试验仍需要独立第三方按本说明提供题目、隔离答案、验收公钥身份和时序。

目录结构（`task_id` 必须与原始公开 manifest 完全一致）：

```text
PUBLIC/
  <task_id>.json                        # 每题 V3.7.25 公开挑战，无私有答案
EVIDENCE/
  <task_id>/
    issuer_receipts/
      issuer_10s.json                    # 10秒单模型协议签名
      issuer_5s.json                     # 组合两臂各5秒协议签名
    solver/
      standalone_10s/
        protocol.json
        solver_manifest.json
        solver_signed_receipt.json
        grader_signed_receipt.json
        score.json
        v3725_ring/fit.json,freeze.json,worker_receipt.json
        v3726_gate/fit.json,freeze.json,worker_receipt.json
      portfolio_5s_each/
        ...（同样的证据文件）
```

每道题由 `research_equibudget_v3729.py` 的 issue / freeze / grade 三阶段，在不同权限域依次执行。每题两套完整签名结算记录必须都存在，且通过 V3.7.28 的 issuer→solver→grader 收据核验才能进入成绩表；**任何不完整、变更或来源不明的证据都应整批报错**。

独立审计侧运行（路径以实际工作空间为准）：

```bash
python research_panel_evidence_v3729.py \
  --plan preregistration.json \
  --manifest public-manifest.json \
  --public-dir PUBLIC \
  --evidence-dir EVIDENCE \
  --backend ./ \
  --issuer-public issuer.pub \
  --solver-public solver.pub \
  --grader-public grader.pub \
  --out-ledger score-ledger.json \
  --out-audit signed-receipt-coverage.json
```

如果 100 道题中有整题**完全未提交**，在签名覆盖报告中列为 `missing_task_ids`，对应的三方法统计时均计 0；不得将它们删出分母。若某题目录已存在却缺少/篡改收据，则拒绝生成有效账本，不得将损坏证据伪装成“自然未提交”。未登记题目目录也拒绝。须在独立第三方核对密钥持有人、设备时钟和私有答案真实来源后，再对组装后的账本进行 grader 签名和最终 summarize。

注意：上述工具能验证**所有已提交任务的逐题密码学签名完整性**，但仍无法凭代码确认签署者是否真是独立机构、持出答案从何而来，以及子进程时钟是否受硬件信任。报告中的独立身份和外部盲测标志始终为 false。内部 CI 的 100 个样例公开题仅验证“1 题完整、99 题缺失”这种失败口径，不是完成 100 道未知数学题。
