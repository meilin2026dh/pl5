# PL5 V3.4 — 统一算子参数注册与跨算子知识迁移

## 一、版本定位与限制

本版本基于 V3.3 完整后端增量开发，不替换旧版源文件、数据库或历史数据。不是自动预测中奖号的产品；没有证明历史开奖具有可利用的预测信息，也不会自动启用 ESSE 正式过滤或下注。

**本版真正完成两条新增参数训练接口和一条有数学全域证明的迁移路径：**

1. **V2.7 BCSE 步长阈值/软惩罚权重联合训练**。在1—9阈值上枚举，以独立均匀模型为基准，使用Beta收缩、训练期评分选模、时间顺序开发期门控以及最终封存测试。开发期没有足够证据时主动回退均匀软约束（惩罚权重0）。
2. **V2.8 Lift 两个模参数学习**。在预先固定的、**不含动态lag**的表达式上，搜索`mod_first`与`mod_second`的2—11候选；对全部10万注的真实特征桶大小精确归一化，在训练区间学习Dirichlet平滑桶分布，在开发区间选择模数，封存测试只评价选中的一组。验证期不足则回退。
3. **V3.3→V3.4 知识迁移**。输入一项已经认证的V3.3模轨道算子和一张新数学真值表，在旧轨道基础上识别最多6处稀疏例外。严格要求100/100表格点重建、长度代理小于原始100格表，才产出新 `research_only` 算子。支持直接在AAN/ESSE科研组合引擎上进行全10万注计算。
4. **统一参数清单**。分类标示`trained_v34`（本版有真实适配器）、`learned_legacy`（历史模块既有学习代码）、`search_only`（有参数但尚未实现训练）等状态。**不是所有参数都已训练**，特别是V2.4窗口/周期、V2.8动态lag表达式及任意数学语言仍未全面可学。
5. **SQLite审计**。研究运行报告以内容SHA256登记、同内容去重并检测篡改；V3.3原有能力库保留。不自动创建任务、不自动晋级算法。

## 二、文件

- `research_backend/pailie5/parameter_hub_v34.py`: 参数规格清单、两个参数学习器、审核记录。
- `research_backend/pailie5/transfer_evolution_v34.py`: 有界、可证明的模轨道→稀疏修补迁移。
- `research_backend/research_v34.py`: `catalog`、`demo`、`fit-step`、`fit-lift`、`transfer`、`audit`。
- `research_backend/pages/22_统一参数注册与迁移研究.py`: 中文Streamlit实验室。
- `research_backend/integration_server.py`: 本地GET `/api/esse/parameters-v34/catalog`、POST `/api/esse/parameters-v34/fit`。只接受受限JSON，不写数据库。
- `research_backend/tests/test_parameter_hub_v34.py`、`test_transfer_evolution_v34.py`、`test_parameter_http_v34.py`。
- `V34_技术实现与验收报告.md`：测试、诊断、限制。

## 三、Windows安装

解压ZIP至新目录，双击`install_to_D_v34.bat`，默认新安装位置 `D:\pl5\research_backend_v34`；如目录已存在**拒绝覆盖**，不会删除原有版本。需要Windows PowerShell、`uv`与Python3.12。

```powershell
# 解压后执行：
.\install_to_D_v34.bat
.\验证_V34.ps1
.\启动_V34_参数与迁移实验室.ps1
```

```powershell
cd D:\pl5\research_backend_v34
uv sync --python 3.12 --group dev
uv run python research_v34.py catalog --report reports/catalog.json
uv run python research_v34.py demo --report reports/demo.json
uv run python research_v34.py fit-step --history "D:\pl5\data\official.csv"
uv run python research_v34.py fit-lift --history "D:\pl5\data\official.csv" --first-pos 0 --second-pos 1
uv run python -m pytest -q tests/test_parameter_hub_v34.py tests/test_transfer_evolution_v34.py tests/test_parameter_http_v34.py
```

官方历史CSV须由用户自己核实号码与期号顺序，自动计算不能弥补来源错误、混入期后数据或数据缺失。CSV兼容前代`research_v24.read_history`读取方式。每次参数训练至少180期、最多10000期。HTTP接口最多1800期，设计为本机loopback-only。

### 跨算子迁移命令

先用V3.3 `research_v33.py table`或`demo`生成SQLite中的已验证算子ID：

```powershell
uv run python research_v33.py demo --registry runtime/v33_metalearning.sqlite
uv run python research_v34.py transfer --source-db runtime/v33_metalearning.sqlite --source-id "pl5.v33.实际ID" --target-table "D:\pl5\data\new_operator_table.json"
```

10x10 JSON表必须是0—2或0—3连续整数类别，与原算子类别数相同；源必须属于V3.3的`affine_orbit`或`sparse_exceptions`类别；超过6个例外/压缩不成立/等价原表均不会制造新能力。

## 四、三种证据层级不能混淆

- **数学全域证明**：100种输入对的数学定义完全一致，可称已证明其有限表等价；不涉及彩票。
- **参数拟合开发验证**：按时间顺序训练、验证并计算模型评分。训练/验证控制多重试验，**不是严格统计预测优势证明**。
- **未来开奖独立前向检验**：本版没有完成官方来源的持续前向验证。彩票若符合独立均匀模型，选择100注的单期覆盖概率仍为0.1%。

## 五、限制

- 首批受控训练仅覆盖V2.7步长阈值、V2.8静态Lift模数；更多历史算子仅被分类登记。
- V3.3内部仍是五类有界10×10数学表模型；迁移路径仅支持沿模轨道进行稀疏修补，不支持任意算子之间无约束迁移。
- 使用的编码bit长度是统一代理，不是真实文件压缩率；Bayeisan/Dirichlet门控仅限此研究假设族。
- 当前环境未直接安装Windows、未执行GitHub前端原生联调、未认证官方实盘开奖数据。
