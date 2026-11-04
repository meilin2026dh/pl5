# PL5 V2.9 — 自主基础数学算子发明实验室

## 本版定位

从 **V2.8 固定安全算子树的组合/变异** 升级为 **直接学习并登记新的有限域基础二元运算**。对数字集合 `D={0,...,9}`，基础运算是冻结的100格真值表 `T:D×D→{0,...,K-1}`，K为3或4。它有真实、完整的数学定义，可供其他算法作为原子能力使用；无需在执行期调用加减乘或构造旧公式树。

**边界**：这是受约束的有限域运算发现机制，不代表AI能够提出全新的数学公理或证明新定理。生成的运算可能只是在既定数据与算法约束下的新数字分区，也不证明有开奖预测优势。

## 新能力

- **两种算子诱导机制**：训练样本的10×10位置对列联矩阵，分别经过谱残差双线性分解和局部残差扩散，诱导3/4值的100格新运算表。最多搜索40种固定候选（10对位置×2机制×2输出基数）。
- **算子独立身份**：输入输出、真值表、训练指纹、数学性质、熵、相邻格变化数，构成UACP风格能力说明书。
- **防重发明**：识别输出标签置换后的等价数字分区，并排除若干基础模运算、比较、绝对差和位异或的简单重编码；这不是所有数学等价关系的完备判定。
- **全空间一致性**：对选定的原子算子，以NumPy查表与独立的纯Python标量调用逐号核验100,000注；注意仅验证同一冻结真值表的执行一致性，不等于独立复现SVD训练过程。
- **时间外证伪**：训练→开发验证→最终封存区间。研究模型使用Dirichlet收缩，验证用固定预测分布的似然比e-value，并按本轮全部候选×权重数目控制家庭错误率。封存区间不参与选模。
- **多空间软约束适配**：选出的算子输出3/4个组，对每组给出模型条件下的软惩罚、组概率及Beta可信区间。可作为后续BCSE新能力研究候选，不能自动成为正式ESSE规则。
- **AAN原生接入**：显式设置`--aan-registry`后，将学习得到的100格真值表注册为`metric=learned_primitive`，允许与时序模式、反延续组成工作流。注册项是`research`状态且绑定训练数据前缀；越过学习截止期回放会被阻断。
- **长期研究**：Windows可在用户显式启用后，每6小时对更新后的历史重新研究；数据库采用追加型科研档案，重复记录不会自行升级预测权限。

## 安装到D:\pl5

将完整ZIP解压，运行根目录`install_to_D_v29.bat`，复制到`D:\pl5\research_backend_v29`。如果目标目录已存在，脚本直接停止，**不会覆盖旧版本或用户数据**。

依次运行`验证_V29.ps1`、`启动_V29_算子实验室.ps1`；电脑需安装`uv`和Python 3.12。

```powershell
cd D:\pl5\research_backend_v29
uv sync --python 3.12 --group dev
uv run python -m pytest -q tests/test_primitive_v29.py tests/test_capability_network_v18.py
uv run python research_v29.py demo --maximum 12 --budget 100 --report reports\v29_iid_demo.json
uv run python research_v29.py biased-demo --maximum 40 --validation-periods 90 --holdout-periods 60 --report reports\v29_bias_demo.json
uv run streamlit run "pages/17_基础数学算子发明实验室.py"
```

真实CSV应由用户核验来自中国体育彩票公告，包含 `issue,date,number`，并按时间排序：

```powershell
uv run python research_v29.py study --history D:\pl5\data\official_history.csv --maximum 40 --validation-periods 60 --holdout-periods 50 --budget 100 --report reports\v29_official_study.json --registry D:\pl5\runtime\v29_research.sqlite --aan-registry D:\pl5\runtime\v29_aan.sqlite --full-ranking reports\v29_all100000.csv
```

仅在核验历史CSV、检查不需要的旧版计划任务后，明确运行`启用_V29_定时研究.ps1`。**安装和启动前端本身不会自动启用后台科研任务**。长期任务在Windows睡眠/关机时不保证运行。

## 研究界限

1. 100注仅指候选规模；公平独立开奖下单期覆盖概率是0.1%。
2. 开发验证证据的e-value家庭错误控制依赖明确的独立均匀零假设、研究范围和固定验证期间。**跨多次自适应任务更换方法、反复查看验证期**不继承单轮保证。
3. 过去训练/验证/封存所用的历史不能当作新未来开奖验证；真实研究仍需开奖前封存并持续前向观察。
4. AAN学习算子不能用于其训练期之前的历史回放。只有一致训练前缀才能复用。
5. 部分研究能力会在后续新增时重复训练生成不同快照；这不等于发现更多本质不同的数学操作。
6. GitHub五序React原生前端没有在本版重新构建；本版提供Streamlit独立科研页面。真实Windows、外网服务和定时任务均需本机验收。
