# 实验算法完整研究版实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将用户上传的实验算法吸收为可复现、可保存、可回放的网站功能。

**Architecture:** 独立纯TypeScript研究模块提供准备好的谓词及诊断信息。排名在完整10万组上预计算；筛选、规则组和候选来源继续复用当前Worker。自动选参内部按时间分割，最后重新拟合。

**Tech Stack:** 现有React、TypeScript、Vite、Vitest、Web Worker；不引入Python服务或新依赖。

**Spec:** ../specs/2026-10-29-experiment-integration-design.md

## Global Constraints

- 原始outputs/实验结果目录只读；测试夹具在work生成后只纳入必要小文件。
- 五位字符串保留前导零；完整排名基准固定100000组。
- 所有参数、参考期、窗口、种子、并列策略随规则和方案保存。
- 预测效力与实现一致性分开表述，不把模拟结果当真实开奖证据。
- 在特性分支完成，保留用户WIP；不将原始实验CSV、HTML报告直接打入前端。

## Review Focus

1. 排名回放不能只对目标一条候选排名；验证同一目标在全量/外部候选下排名判定一致。
2. 自动选择不得读入验证答案训练；改变后续答案不能改变更早切点拟合。
3. 全并列时精确N与边界全收的含义不同；零信号需要显示退化。
4. D-S分窗余数不能丢，极端冲突不能输出NaN或Infinity。
5. 历史/参数变化使诊断和过滤结果同时失效；JSON恢复完整研究配置。

---

### Task 1: 统计过滤与公式夹具

**Files:** Create src/domain/research/types.ts, statistics.ts, filters.ts; tests/research-filters.test.ts, tests/fixtures/research-reference.json; docs/research/experiment-audit.md.

**Interfaces:** ResearchConfig包含method、window、referenceIssue、数值参数、保留比例、并列策略和seed。prepareResearch(config, history)返回 {test(number):boolean, diagnostics:ResearchDiagnostics}，不依赖React。

- [ ] 用固定历史、前导零和手算小样本建立失败测试；对冷热TopK、贝叶斯阈值、Markov、sigma、分位数、形态频率、邻号和多重集分别断言。
- [ ] 从源Python只读运行生成夹具，记录公式与参数，测试TS输出与Python谓词一致。
- [ ] 实现统计快照、参数校验与公式；零方差时采用数学标准差0并记录与源or1回退的差异，遗漏未知不当精确值。
- [ ] 执行该模块测试，记录red→green证据。

### Task 2: 评分、模型融合与排名

**Files:** Create src/domain/research/models.ts, ranking.ts; tests/research-models.test.ts.

**Interfaces:** fitScores(config, stats)返回 {score(number):number, details}；rankSelection(config, model)返回全量号码保留集合与排名诊断，由Task1的prepareResearch路由。

- [ ] 建立失败测试：概率归一化、七模型权重和为1、均匀历史退化、source Python分数对照、前导零、固定seed重现、全并列N条/全部100000条两种策略。
- [ ] 实现稳定logGamma与log-sum-exp、热度、BMA、DS-IDM、Dempster和真实命名的单位置最佳模型。
- [ ] Dempster均衡分窗覆盖全部记录，保存每步冲突；近全冲突明确失败。
- [ ] 全量100000排名预计算，明确量化精度和并列规则；外部大底只在之后取交集。
- [ ] 执行模块测试和性能测量。

### Task 3: 自动选择与无未来数据验证

**Files:** Create src/domain/research/tuning.ts, presets.ts; tests/research-tuning.test.ts.

**Interfaces:** tuneResearch(config, history)返回选中参数/组合及逐折覆盖与平均保留数；最终由prepareResearch重新拟合。presets导出57候选定义和A—F组合包。

- [ ] 失败测试：训练/验证隔离、重复号码按期计数、目标不可达时回退、候选并列确定性、贪心达到目标后收敛、三种选择标准。
- [ ] 实现滚动训练/验证、三种选择标准与57候选贪心，验证掩码不能用全历史拟合。
- [ ] 复用已缓存的折统计和候选掩码，避免每候选反复构建全量统计；输入长度不足明确报错。
- [ ] 执行针对性测试。

### Task 4: 规则引擎、回放、方案集成

**Files:** Modify src/domain/pick5.ts, advanced.ts, backtest.ts, src/lib/plans.ts（仅需要时）；tests/backtest.test.ts, plans.test.ts, research-integration.test.ts.

**Interfaces:** 新研究规则kind及ResearchConfig纳入Rule类型、标签、校验、准备谓词；FilterResult允许附带诊断。现有规则格式向后兼容。

- [ ] 先测研究规则包含/排除、分组容错、外部大底、截止期、JSON备份恢复、逐期回放一致性。
- [ ] 注册研究规则并严格验证；回放每期使用此前历史，排名仍以全量100000构建。
- [ ] 在Worker保留请求标识、取消与错误协议；输入变更废弃诊断。
- [ ] 执行集成及现有回归测试。

### Task 5: 实验方法界面与交付

**Files:** Create src/components/ResearchRules.tsx, research.css；Modify Workbench.tsx、App.tsx帮助、必要高级规则显示路由；tests/research-ui.test.tsx；README.md与验证记录。

**Interfaces:** ResearchRules接收FilterInput/onChange，使用统一配置校验并添加/编辑研究规则；已计算诊断来自FilterResult，不在主线程执行全量模型。

- [ ] 先测方法选择、参数校验、添加/编辑、历史缺失提示、方案复现以及条件变化使结果失效。
- [ ] 实现分组方法、窗口与参考期、保留比例/并列/种子、选参标准及诊断信息，保持橙色视觉。
- [ ] 补充公式说明、来源审计、模拟实验结论与已修正差异；不把best-model称为BMA。
- [ ] 执行完整pnpm test、pnpm typecheck、pnpm build；浏览器核验研究规则→保存→恢复→计算→历史回放及移动布局。
- [ ] 简化检查及独立完整代码审查，修复有效发现；更新研发笔记并生成可运行交付包。发布沿用已授权仓库与账号，提交前核验远程状态。
