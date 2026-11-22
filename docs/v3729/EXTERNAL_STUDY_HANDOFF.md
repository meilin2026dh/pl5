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
3. 独立评分人在持出答案结算后出具两份 JSON（见下），然后运行 summarize --plan preregistration.json --manifest public-manifest.json --private-metadata private-metadata.json --ledger score-ledger.json --out unverified-summary.json。汇总器要求 ledger 同时保存 preregistration_sha256 和 public_manifest_sha256，且私有分类 ID 必须与公开任务逐项一致。

其中 score-ledger.json 必须包含 schema=pl5-v3729-score-ledger-1、solver_source_commit 及 results 数组。每条记录包含 task_id、arm、status、holdout_errors、holdout_cells、budget_ms、receipt_verified。receipt_verified=True 只是**独立审计完成后写入的结果字段**；本脚本不会自己验证那个字段代表的三方签名链或硬件时钟真实性。

private-metadata.json 的 schema=pl5-v3729-private-strata-1，categories 为 task_id -> structured / negative_control / out_of_grammar 的映射。此文件只能在求解冻结后由评分方提供，不应让求解端接触。

本模块输出始终标注 external_blind_verified=false、trusted_timestamp_verified=false、lottery_predictive_advantage=NOT_ESTABLISHED；无论统计显著与否均不自动升级认证等级。

## 五、当前阶段通过与未通过的边界

已实现：
- 100份公开挑战的逐字节 SHA256 和字段校验，防止私有标签出现在公开 JSON；禁止重复任务、重复坐标、输入范围越界、目录符号链接逃逸。
- 全部题目计入分母，缺失按失败处理；负对照不少于25道；同预算结果核验。
- 预注册文件不能覆盖，冻结 commit 与环境摘要必须完整；统计提供 exact McNemar 和描述性区间。
- 仅针对内部合成题面运行 Windows/Linux Python 3.12 CI。

仍未实现或未取得：第三方出题者的真实独立身份和私有密钥，可信外部时序，独立硬件与容器镜像签名，100道任务真实求解，成绩提交的签名记录自动核验，跨题族稳健显著性，以及彩票未来开奖前的长期前向检验。这些缺失不能用模拟结果弥补。
