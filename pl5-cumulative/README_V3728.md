# PL5 V3.7.28 — 签名证据链与可交接的独立盲测协议

本轮**不增加选号规则，不声称独立盲测成功**。建立可供外部出题者、求解方、评测者分别运行的可审计接口。依赖 `Python>=3.12` 和 `cryptography>=43`（任选 `pip install '.[audit]'`），原有数学求解模块不改动。

## 角色与命令

在不同管理主体的机器上分别生成私钥，不能把三个私钥随正式挑战包分发。以下示例使用 `research_backend/` 为当前目录：

```bash
python research_signed_blind_v3728.py keygen --private issuer.key --public issuer.pub
python research_signed_blind_v3728.py keygen --private solver.key --public solver.pub
python research_signed_blind_v3728.py keygen --private grader.key --public grader.pub
```

出题方先用 `research_open_grammar_v3725.py prepare --challenge challenge.json --public PUBLIC --private PRIVATE` 生成公开与私有两份材料。**出题方只交付 `PUBLIC/public_challenge.json`、`issuer_attestation.json` 和核实身份后的 `issuer.pub`；`PRIVATE/private_challenge.json` 严禁发送给求解方。**

```bash
python research_signed_blind_v3728.py issue --challenge-public PUBLIC/public_challenge.json --backend-root . --issuer-private issuer.key --issuer-public issuer.pub --out issuer_attestation.json --budget-ms 5000
python research_signed_blind_v3728.py freeze --challenge-public PUBLIC/public_challenge.json --backend-root . --issuer-attestation issuer_attestation.json --issuer-public issuer.pub --solver-private solver.key --solver-public solver.pub --out SOLVER
python research_signed_blind_v3728.py settle --challenge-public PUBLIC/public_challenge.json --challenge-private PRIVATE/private_challenge.json --backend-root . --issuer-attestation issuer_attestation.json --issuer-public issuer.pub --solver-public solver.pub --grader-private grader.key --grader-public grader.pub --out SOLVER
python research_signed_blind_v3728.py verify --challenge-public PUBLIC/public_challenge.json --backend-root . --issuer-attestation issuer_attestation.json --issuer-public issuer.pub --solver-public solver.pub --grader-public grader.pub --out SOLVER
```

**必须由三个不同的人或组织持有私钥、独立保存日志，在独立外部时间源公示冻结截止后才可宣称由外部组织执行了盲测**。单台机器上复制三个角色不能证明独立性。系统验证 Ed25519 签名与部分 Python 研究源码 SHA256，但不证明真实身份、时序先后或代码的全部运行时依赖；没有提供安全沙箱/远程证明，不应把自签证据等同于公证。

## 固定的评分与预算

- 两个算法各按相同 wall-clock 上限运行独立子进程，从 Python 启动、加载依赖、拟合、冻结到证据写入均计入，超时即弃权；代码基于 V3.7.27。
- 组合模型若两条链路都运行，最多承担两倍预算，因此在报告中始终单独列示，不作为同成本赢家。
- 任务整体分母包含无解、弃权、失败、超时，不能只从接受的任务统计正确率；私有测试不得用于训练、结构或参数选择。
- 任务生成与人工研发成本、外部方招募、环境准备、第三方评分耗时仍未计入该模型子进程预算；不能称为总科研等算力对照。
- 外部盲测必须预先冻结任务规模、任务来源、数据权限、负对照比例和接受/弃权评价规则。推荐目标至少100个完整数学任务，包含未见过的任务族和无结构负对照；事前登记可拒绝阈值与一次性统计检验。

## 科研局限与下一步

代码持出库分为公开训练/验证与仅出题和评分者可见的隐藏集；签名防篡改仅对已公开的公钥有效，不确保公钥所有人就是外部出题机构。只有**经过外部方独立交付任务、提前冻结代码、身份核验、可信截止时间证明、第三方保管持出标签并独立评分**的整套执行流程，才可改写证据等级。本轮开发者自己编写的测试属于内部验收，与开奖结果预测优势无关。
