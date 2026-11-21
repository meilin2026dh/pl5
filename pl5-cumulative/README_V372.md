# PL5 V3.7.2：表达式树结构搜索与冻结验证

## 本轮做了什么

复用已有 V3.0 整数表达式树解释器，而不是重新建立数学语义：
- 子树替换、收缩、包装、交叉，以及运算符/常量叶节点变异。
- 通用语法组合、束内候选竞争、复杂度惩罚和整数行为去重。
- 拟合接口只接收训练单元；保留单元与完整真值表仅在算子冻结后用于评价。
- 独立标量解释器核验100个输入对；交换律、结合律、单位元及明确反例。
- 冻结算子 JSON 导入导出，SHA256 完整性检查和不重新拟合的复用。
- 修复 V3.7.1 包级导入错误；统一包元数据为3.7.2。

旧模块不被新算法替换；新模块也不会自动写入生产过滤规则。

## 运行

要求 Python 3.12+。沿用 `research_backend/pyproject.toml` 中依赖，不配置 API Key。
在已安装项目依赖的环境中，进入 `research_backend` 后执行：

```text
python research_v372.py demo --output runtime/v372_demo
python research_v372.py benchmark --output runtime/v372_benchmark
python -m pytest -q
```

输出目录必须尚不存在，防止覆盖既有实验结果。同种子复跑请使用另一个新目录。

自有运算表的观测数据用 JSON 数组，每项是 `[输入a, 输入b, 输出值]`，均为0—9整数。
同一数据文件内不能重复输入对。只把训练单元写入训练文件，例如：

```json
[[0,0,0],[1,2,3],[3,4,7]]
```

```text
python research_v372.py fit --input train_cells.json --output runtime/my_operator
python research_v372.py evaluate --operator runtime/my_operator/operator.json --input heldout_cells.json
```

默认阻止训练与评价输入对重叠。此接口面向有限运算表，不是按时间排列的开奖记录。

## 新增代码

| 文件 | 职责 |
|---|---|
| `pailie5/structure_ast_v372.py` | AST校验、简化、变异、交叉；复用V3.0解释器 |
| `pailie5/structure_search_v372.py` | 训练单元数据结构、有界搜索、冻结算子、搜索轨迹 |
| `pailie5/structure_evidence_v372.py` | 留出评价、逐格证书、代数反例、导入导出 |
| `research_v372.py` | 离线fit/evaluate/demo/benchmark入口 |

## 验证与结果

详见 `docs/v372/VERIFICATION.json`、`docs/v372/RESEARCH_REPORT.md`。
本轮新日志在 `docs/v372/evidence/`，不得把根目录中继承的旧日志当成本轮结果。

18组开发阶段合成实验：五类已知结构×3种随机种子均在全100格上精确重建；
3个独立随机表的保留单元总计正确8/90，无完整重建。相同种子再次运行，除耗时外结果完全一致。

## 科学边界

本轮10个基础运算符、6个常量和最大15节点/8层的限制仍由人指定。
实际默认上限为11节点/6层、12000次表达式评价、30代。
本轮已知结构的精确解主要来自通用语法组合；尚不能证明变异/交叉相对枚举的独立贡献。
所谓“压缩”是明确共享码本下的编码长度诊断，不是最短公式的数学证明。
100格全等只证明该有限定义域上的等价；不证明数学史上的新颖性，也不证明彩票过滤优势。

不受限递归、任意代码生成、真正的新原语发现、代数同构去重以及跨真实任务迁移仍未完成。
没有把同一规则在训练表和测试表分别拟合后称为“零样本迁移”。

## 包与部署范围

本包保留上传累计包的可交付源文件；仅排除`.git`、Python字节码、pytest缓存等非源码产物。
`PRESERVATION_AUDIT_V372.json`记录原文件保留与明确改动；`SHA256SUMS_V372.txt`记录交付校验值。
原包中部分中文路径已经存在编码乱码，本轮保持历史路径以便追溯，没有擅自重命名旧安装脚本。
旧安装脚本对应其原版本，不代表已完成V3.7.2部署。
本轮未修改用户的D盘，未同步GitHub，未运行完整React生产构建，也未在Windows实机验收。
