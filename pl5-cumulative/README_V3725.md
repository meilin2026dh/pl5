# PL5 V3.7.25 — 模10动态语法扩展及外部挑战交接协议

本版完整累计包在V3.7.24原始文件基础上迭代，不删除已有源码、试验、封存证据。范围是**科研试验**，不应用于投资或购彩决策。

## 研发结果及边界

- 新增四级语法：原有特征、三次多项式项、条件门控项、奇偶门控项。
- 在训练样本上分别求解模2及模5线性系统，再由中国剩余定理复原模10表达式系数；每级输出至多一个候选完整表，随后只用验证集冻结候选。
- 研究者定义9类×4个**未用于V3.7.25初始调试**的种子，共36项内部合成实验，训练/验证/持出48/16/36格。上一版扩展搜索接受4项，新引擎接受20项，接受后720个持出格零错误；新引擎另16项弃权。结果见`docs/v3725/RESEARCH_REPORT.md`。
- **这是开发者设计的合成任务，不是外部独立盲测**。特征词表仍由开发者事先定义，不是无限开放数学语法，也不是新数学定理。
- 两臂候选评估次数和总代码执行成本**不匹配**；不宣称正式效率优势或算法普适优越。
- 排列五预测能力：**尚未证明优于等预算随机选号**。

## 核心文件

- `research_backend/pailie5/open_grammar_v3725.py`：有限域语法求解、学习及候选冻结、数据分区交叉验证、摘要承诺及单次结算。
- `research_backend/research_open_grammar_v3725.py`：真实外部挑战可以使用的公开/私有文件交接协议。
- `research_backend/benchmark_open_grammar_v3725.py`：内部36项研究实验，比较V3.7.24扩展搜索与新阶段求解。
- `research_backend/tests/test_open_grammar_v3725.py`：新模块单元测试。
- `docs/v3725/examples/synthetic_challenge.json`：第一方可重复样本（**非外部盲测**）。
- `runs/v3725/demo/`：公开/私有文件格式演示；完整包同时包含样本私有文件，**不可当成独立盲测**。

## 使用

在 `research_backend` 目录：

```bash
python -m pip install -e '.[dev]'
python -m pytest -q tests/test_open_grammar_v3725.py
python benchmark_open_grammar_v3725.py ../runs/v3725_NEW_STUDY
```

外部独立评测建议由独立出题者在**物理/账户权限隔离**的环境执行：

```bash
# 出题者单独掌握完整挑战文件和私钥nonce，生成公开及私有文件
python research_open_grammar_v3725.py prepare --challenge challenge.json --public PUBLIC --private PRIVATE
# 解题者只能得到PUBLIC目录
python research_open_grammar_v3725.py solve --public PUBLIC/public_challenge.json --out SOLVER
# 出题者验证SOLVER中已有冻结结果后，凭PRIVATE目录进行一次性结算
python research_open_grammar_v3725.py grade --public PUBLIC/public_challenge.json --private PRIVATE/private_challenge.json --out SOLVER
```

本地文件SHA256能发现常见的内容修改，但**不能单独证明第三方身份、开奖前时间或权限隔离**；应将公开承诺文件由独立评测方进行可信时间戳/公开公证，并保存外部审计记录。不得把文件内的自填`source_description`当成外部验证身份。

**尚未验收**：Windows `D:\pl5` 实机部署、独立第三方出题盲测、真实彩票前向长期试验、GitHub主线合并。
