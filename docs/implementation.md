# v0.1 实现与交付记录

范围以[独立方案书](https://chatgpt.com/space/page_34895bfa5f0c81919e5ba12e662b6b8e)为准。此次完成已定义过滤、历史观察、方案复现与回放核验功能。

## 对应实现

| 范围                             | 实现位置                                                |
| -------------------------------- | ------------------------------------------------------- |
| 定位、基础指标、胆拖/杀号        | domain/pick5.ts、components/Rules.tsx                   |
| 形态、位置、两位运算、分类与余数 | domain/advanced.ts、components/AdvancedRules.tsx        |
| 历史参考、重邻孤、遗漏、频次     | domain/advanced.ts、lib/history.ts                      |
| 外部大底、集合运算               | lib/candidates.ts、components/CandidateSource.tsx       |
| 规则组容错                       | domain/pick5.ts、domain/advanced.ts                     |
| 保存、恢复、JSON备份             | lib/plans.ts、App.tsx                                   |
| 六种历史图与真实数据             | pages/History.tsx、server/provider.ts、server/index.mjs |
| 逐期历史回放                     | domain/backtest.ts、components/Backtest.tsx             |

## 交付边界

- 已定义F01—F34纳入实现；C01—C08待验证术语仍为候选，不编造市场私有口径。
- 本机单用户工具，无账号、支付、代购功能。部署采用Node24静态服务加数据代理。
- 官网数据实际验证2000条，覆盖2021-02-03至2026-10-18；来源与版本随快照保存。官方服务不可用时降级到有标记缓存。
- 过滤结果输入变更失效，历史回放禁止未来数据；参数与导入统一校验。

## 验证

自动测试覆盖基础/进阶公式、历史边界、集合运算、方案导入、Worker取消/失效、历史页异步竞争。生产构建及TypeScript检查通过。浏览器实测全量10万组、形态通配过滤、真实历史获取、桌面与移动布局。最终运行结果见交付验证记录与代码审查记录。
