# PL5 V3.7.18 — 共享评分内核与GitHub累计科研源码复原

## 本版改动

- `research_backend/pailie5/probability_ranker.py`: 两条排名路径统一调用 `_rank_core_v3718`，完整排名仍输出10万行审计表，`rank_target_snapshot_v3717`仍只输出冻结排序和目标查找结果。
- `research_backend/tests/test_shared_rank_core_v3718.py`: 先失败再修复的TDD测试，验证同一函数执行、手工规则选择、前导零和全表一致。
- 保持已有 `BasicFilterCatalog`、`GA-CS`、时序雕刻、共形科研、历史规则与自动数学研究模块不变。

## 检验范围

- 完整科研后端：877项通过。
- 历史跨模块集成：29项通过。
- 跨版本输出指纹：完整10万行表、规则元数据、概率数组、目标排序、五期滚动报告共6类全部相同。
- 性能比较需以完整报告里写明的实际CPU、测试数据、运行环境为准；不能从一次测量推导普遍加速比。

## GitHub 状态

`research/v3718-shared-score-source-baseline` 已引入累计科研后端、历史兼容组件及冻结实验依赖的596项文本源文件，与本地逐文件 Git blob SHA 匹配；根 `README.md` 特意恢复Web项目原版。

GitHub还没有覆盖所有历史压缩包中的日志、展示用大CSV以及二进制资产，也未在你的Windows D:\\pl5上测试。`main` 不受这次研究分支同步影响。以完整累计zip为历史留存权威基线，以GitHub研究分支为文本研发源码。
