# 自适应概率实验室 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans; implement inline, with one independent final review.

**Goal:** 实现已确认的八方向概率实验室，区分校准集合、预算组合和理论覆盖。
**Architecture:** TypeScript纯函数模型/集合/运输/在线模块，由独立Worker编排，React卡片接入既有工作台。
**Tech Stack:** React19、TypeScript、Vite、Vitest，无新依赖。
**Spec:** ../specs/2026-11-01-adaptive-probability-design.md，用户已答“要”，确认实施。

## Global Constraints

保持五位字符串、历史截止期和先预测后更新；最终测试不决定门控；预算截断不继承Conformal保证；理论精确覆盖恒n/100000；沿用浅橙UI及方案保存；详细笔记Obsidian。

## Review Focus

- 默认配置首次保存不能取消自身任务，修改/取消后旧回复不得恢复结果。
- 均匀概率并列应保留全集；极高覆盖小样本顺序统计溢出取无限阈值。
- 测试期改变不得改变训练门控、校准阈值、预算组合。
- 完整前缀修订须重建在线状态；参数重跑不能洗掉已查看测试标记。
- 大底/旧条件相交不能保留原覆盖声明；载入支持撤销且保护后续编辑。

### Task 1: 数学内核
**Files:** src/domain/probability/{config,models,sets,transport,online}.ts；tests/probability-core.test.ts。
**Interfaces:** fitModel(kind,rows,strength)→JointModel；pmf(model)→Float64Array；conformal(probabilities,calibration,target)→集合；transportProfile(mask,pmfs)→分层质量；onlineReplay(train,later,strength,source,previous?)→轨迹及状态。
- [ ] 写测试：归一、边际似然独立计算、MDL对应、同分与无限阈值、W1手算、在线遗憾/幂等/修订；先运行确认缺模块失败。
- [ ] 实现固定U/I/J1/J2、BDeu计数与预序贯证据、LAC、汉明BFS和分数背包、在线log权重。
- [ ] 运行核心测试，必须全部通过。

### Task 2: 编排与方案集成
**Files:** src/domain/probability/engine.ts；src/domain/pick5.ts；tests/probability-engine.test.ts。
**Interfaces:** analyzeProbability(input,config,progress?,previous?)→ProbabilityResult；复用质量检查与researchHistory截止期、filter原始来源。
- [ ] 写时间隔离/坏数据/预算冲突/联合强依赖/规则域及配置往返测试，观察失败。
- [ ] 实现训练前部选模、60期门控、冻结重拟合、四模型集合/JS/撤销敏感性、预算组合二/三元覆盖、W1、在线轨迹及报告。
- [ ] 跑领域集成测试，类型检查。

### Task 3: 页面与持久记录
**Files:** src/components/ProbabilityLab.tsx；src/workers/probability.worker.ts；src/pages/Workbench.tsx；tests/probability-ui.test.tsx。
**Interfaces:** ProbabilityLab({input,onChange})；Worker请求{id,input,config,previous}，回复stage/result/error。
- [ ] 写真实引擎Worker协议UI测试，先确认组件缺失失败。
- [ ] 实现参数、结果表/曲线、集合查询、预算载入撤销、复制、取消、失效、完整前缀在线存档与已看测试登记。
- [ ] 跑UI与全套测试；构建；实际浏览器操作及截图。

### Task 4: 复核交付
- [ ] 独立只读审查，处理具体缺陷并补回归。
- [ ] 更新仓库文档与Obsidian，记录真实测试/页面/数据范围及限制。
- [ ] 仅提交本轮文件，按已有授权推送并核对远端源码树。
