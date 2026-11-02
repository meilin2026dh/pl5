# PL5 V1.x–V3.6 全版本功能审计台账

审计基线：main 9eb9ec5ad542877680755bccf27345298ef7b99f；研究分支 research/v36-dual-engine-integration。
注意：历史研究编号与 Git 提交不是一一对应关系；不得仅凭提交日期宣称版本验收。

| 功能族 | 已确认 Git 提交 | 已确认源码/测试线索 | 结论 |
|---|---|---|---|
| 基础选号、历史分析、过去数据回测 | 427184440 | src/domain/pick5.ts、backtest.ts | 主线已存在；本轮未重跑 |
| 统计研究、评分与调参 | d47be6391 | src/domain/research/ | 主线已存在；需逐项测试 |
| 空间形态与数字几何 | d47be6391、e991ff3f3、b81fd353d | src/domain/geometry.ts | 主线已存在 |
| 跨期关联 | 70f04be92 | src/domain/relations.ts | 主线已存在 |
| 数学数字特征 | 1dc01c318 | src/domain/math.ts | 主线已存在 |
| 动态冷热与残差 | a9a54b39e、744eab5d7 | src/domain/research/potential.ts、audit/ | 主线已存在 |
| 多阶段选号、学习与组合回放 | f30196ad7 | src/domain/selection/ | 主线已存在 |
| 软排序与覆盖优化 | ca83f3855 | src/domain/innovation/ | 主线已存在 |
| 随机性与稳健性证据 | ad458021b | src/domain/evidence/ | 主线已存在 |
| 序列、约束、在线后验 | 2c32e5899 | src/domain/lab/ | 主线已存在 |
| 概率校准、稳健组合 | bd2b76cbb | src/domain/probability/ | 主线已存在 |
| 密度比、张量列车、DPP | 65e659554 | src/domain/discovery/ | 主线已存在 |
| 联合注意力、图、对比模型 | 9c1d6846b | src/domain/discovery/ | 主线已存在 |
| Copula、孤立、最大熵、自编码、小波 | 9eb9ec5ad | src/domain/discovery/ | 主线已存在 |
| V2.7 贝叶斯约束满足的指定版本验收 | 未定位独立版本标识 | 需对照 probability/lab 模块 | 待审计 |
| V2.8 自主升维表达式的指定版本验收 | 未定位独立版本标识 | 需核对源码与原实验 | 待审计 |
| V2.9 基础算子发明的指定版本验收 | 未定位独立版本标识 | 需核对源码与原实验 | 待审计 |
| V3.1–V3.3 元学习的指定版本验收 | 未定位独立版本标识 | 需核对源码与原实验 | 待审计 |
| V3.4 双引擎 | 9120a30d、7c84841c | innovation/dualEngine.ts | 研究分支部分实现 |
| V3.5 固定过滤率误删评价 | 9120a30d | innovation/dualEngine.ts | 研究分支部分实现；原实验未迁移 |
| V3.6 有限表算子学习 | 7b7a3886、c2566d7 | innovation/operatorEvolution.ts | 研究分支原型 |

## 补做原则
1. 先确认现有实现，缺什么补什么，避免覆盖原模块。
2. 每一版本映射：需求、源码、测试、数据、运行命令、证据、状态。
3. 不允许使用历史提交说明中的“测试通过”代替当前 CI 运行。
4. 任何自动发现的过滤因子必须默认禁用，只有样本外显著性与误删率基线评价通过后才能作为研究候选；不能宣称真实开奖优势。
5. 不能证明存在的历史功能标记“待重建”，不能擅自标记“完成”。

## 尚待完成
- 获取并核对历史 V1.x–V3.5 的原始规格与独立实验产物。
- 补充自主升维、算子元学习、非因果异常关联滚动验证的完整实现与接口。
- 运行 pnpm test、pnpm typecheck、pnpm build；检查 CI。
- 生成逐版本验收矩阵并核对主分支合并前的回归结果。
