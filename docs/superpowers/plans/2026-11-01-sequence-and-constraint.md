# 时序与约束实验扩展 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans; implement inline and request one independent final review.

**Goal:** 完成用户已确认的时序模型、增量后验、有限覆盖优化及能力登记。
**Architecture:** 纯TypeScript数学内核，由独立Worker执行；既有精选scorer扩展，新实验卡片共享历史/配置/方案与载入撤销模式。
**Tech Stack:** React、TypeScript、Vitest、Vite，无新依赖。
**Spec:** ../specs/2026-11-01-sequence-and-constraint-design.md（用户已确认）

## Global Constraints

上下文严格早于目标；训练/验证/诊断时间隔离；全参数训练与梯度检查；后验为可信区间；有限域最优不冒称全集最优；n/100000边界不变；沿用Worker取消、陈旧消息拒绝与Obsidian详细记录。

## Review Focus

- 窗口滑出、完整前缀修订及损坏缓存不能错误沿用计数。
- 神经训练必须更新嵌入、门/注意力和输出层；因果mask不可泄漏未来。
- 中断/超限不发布未完成模型；最终诊断不能选择epoch或权重。
- 限制终止的最优界必须来自全待搜索前沿，不使用当前节点界。
- 默认配置首次保存不自取消，载入撤销保护后续编辑。

### Task 1: 增量后验和有限求解
**Files:** src/domain/lab/{config,beta,posterior,cover}.ts；tests/lab-core.test.ts。
**Interfaces:** updatePosterior(rows,config,source,previous?)→50格均值/区间/可验证状态；solveCover(candidates,targets,config,clock?)→状态/值/全局界/认证。
- [ ] 测试先行，观察缺模块失败；Beta独立参考、追加等于重算、修订/损坏、滑窗、子集穷举/空域/限制/gap。
- [ ] 实现Beta CDF/逆CDF、验证缓存后的真实增量计数、有界bitset分支定界与独立覆盖认证。
- [ ] 核心测试通过后进入下一任务。

### Task 2: 真实时序模型
**Files:** src/domain/selection/{autodiff,sequence}.ts；selection/{config,learning,engine}.ts；tests/sequence.test.ts。
**Interfaces:** sequenceLoss(kind,weights,context,target)→loss/probabilities/gradient/attention；fitSequence(rows,kind,seed,config?)→评分/诊断；scorer枚举扩展兼容旧值。
- [ ] 先写梯度/因果性/学习合成/时间切分测试，观察失败。
- [ ] 实现LSTM与单层因果Transformer、全参数反传、早停及固定epoch重拟合、验证锁定收缩混合对照。
- [ ] 接入精选/回放与资源上限，运行相关测试与类型检查。

### Task 3: 页面、管道和持久记录
**Files:** components/SequenceResearchLab.tsx、SelectionLab.tsx；workers/lab.worker.ts；domain/lab/{engine,registry}.ts；domain/pick5.ts；pages/Workbench.tsx；tests/lab-ui.test.tsx。
**Interfaces:** analyzeLab(input,config,task,previous?,progress?)→后验或覆盖报告；方法登记包含类型/量纲/最小历史/回放/校准支持。
- [ ] 写真实引擎Worker协议和配置往返测试，先观察缺功能失败。
- [ ] 新增后验/覆盖卡片、时序训练配置/曲线/注意力、方法目录与执行阶段；复制、载入/撤销、取消及旧回复防护。
- [ ] 官方历史实际操作及报告回读；全套测试、构建与格式检查。

### Task 4: 复核与交付
- [ ] 独立只读代码审查，修复具体缺陷并回归。
- [ ] 更新源码说明、研究实录及Obsidian（状态与实测一致）。
- [ ] 按已有授权提交/推送，只用meilin2026dh，核对远端源码树。
