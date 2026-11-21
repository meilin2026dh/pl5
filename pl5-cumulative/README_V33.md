# PL5 V3.3 — 算子结构、参数与数学性质统一元学习引擎

**版本定位：** 在 V3.2 完整源码上增加 `Operator Meta-Learning Engine`。当前交付为可执行的、受控的有限数学算子学习工程，并非能够从无限数学语言中自行发明公理的通用科学家。

## 1. 核心成果

建立算子三层表示：

\[
\mathcal O=(S,\theta,\mathcal C),\qquad (a,b)\in\{0,\ldots,9\}^2.
\]

- `S` **结构层**：可选择五类受控模型，包括模轨道、分段轨道、稀疏修补、深度≤3的条件树、带连续实数系数的量化线性模型。
- `θ` **参数层**：离散模系数、方向参数、轨道查找表、行分组、例外点、分支特征和阈值、叶标签、连续系数均具有实际拟合过程。不同类型分别使用枚举、条件频数、兼容分组、贪婪树生长或最小二乘与局部校准。
- `C` **性质层**：检测六项可证数学性质（交换、两类循环平移不变、仅依赖单输入、输出域限制下的结合律）；可声明必需性质，不成立则拒绝，不能靠调节学习结果伪造性质。

**边界：** 不是此前PL5所有历史算子都完成了统一参数学习；现在统一实现的是以上五类有限家族。表的输出目前只支持连续整数类别 `0..2` 或 `0..3`。推断搜索具有明确容量限制。性质字典也是预声明的，不会自动创造任意新公理。

## 2. 算法与验收原则

1. 对同一张10×10数学表，先随机保留20个单元作为**模型诊断**，在剩余80格拟合各家族，记录误差；此诊断不是未来开奖独立验证。
2. **随后重新用全部100格学习**结构及参数，只登记能够与原始运算表逐格完全一致、且代理描述长度短于直接记录整个表的算子。公开区分诊断与全表证明，避免数据泄漏假象。
3. 每个登记能力都必须经过 NumPy批量求值、逐格标量求值、SHA256数学表指纹、性质一致性验证。登记采用SQLite主键和校验，状态固定 `research_only`。
4. 不支持从文本执行任意Python代码，不自动改变正式彩票过滤权重，也不自动投注。
5. 原始表容量代理为 `100 × ceil(log2(k))` bit；压缩代理是统一内部计算模型，**不是实际zip压缩文件大小**。
6. 数学发现与彩票预测应完全区分：真实开奖结果若独立均匀，任何基于历史的模型都不能可靠提高中奖概率。

## 3. 项目文件

- `research_backend/pailie5/operator_metalearning_v33.py`：数据结构、学习器、数学性质校验、100格证明与能力库。
- `research_backend/research_v33.py`：`demo/table/study/schema/registry` CLI命令。
- `research_backend/pages/21_算子元学习与性质发现.py`：Streamlit中文可视化工作台。
- `research_backend/integration_server.py`：新增本机HTTP GET `/api/esse/meta-v33/capabilities`、POST `/api/esse/meta-v33/learn`。
- `research_backend/tests/test_operator_metalearning_v33.py`、`tests/test_meta_http_v33.py`：专项回归测试。
- `V33_技术实现与验收报告.md`：实验数据和局限。

## 4. Windows安装

1. 解压ZIP到独立临时文件夹，双击 `install_to_D_v33.bat`。
2. 源码会安装到 `D:\pl5\research_backend_v33`。已有同名目标目录时**拒绝覆盖**；原有 `D:\pl5\data`、`runtime`、旧版本与React前端不修改。
3. 需有 Windows PowerShell、Python 3.12、`uv`；运行 `验证_V33.ps1` 自动安装当前Python项目依赖，并执行专项测试和演示。
4. 运行 `启动_V33_元学习实验室.ps1` 在浏览器使用中文实验室。

终端命令：

```powershell
cd D:\pl5\research_backend_v33
uv sync --python 3.12 --group dev
uv run python -m pytest -q tests/test_operator_metalearning_v33.py tests/test_meta_http_v33.py
uv run python research_v33.py demo --report reports/v33_demo.json
uv run streamlit run "pages/21_算子元学习与性质发现.py"
```

用户自己的10×10数学表（JSON二维整数数组）：

```powershell
uv run python research_v33.py table --table-json "D:\pl5\data\operator.json"
```

使用经过用户核实的官方历史CSV诱导数学表，只用**前缀历史**，最后110期不参与诱导：

```powershell
uv run python research_v33.py study --history "D:\pl5\data\official.csv" --maximum 4
```

这不会自动对110期进行彩票预测；若要检验预测价值，必须另建事先冻结的模型和正式时间外评估。

## 5. 自主研究任务

可以**手动**使用 `启用_V33_定时研究.ps1` 创建每天 00:20、06:20、12:20、18:20 的Windows任务，默认采用合成数学表。已运行的旧版任务需要用户检查并停用，不自动接管或覆盖；停止任务使用 `停止_V33_定时研究.ps1`。

HTTP接口默认本机，只允许传入JSON数学表，不会向SQLite自动写入外部调用结果。**React原生前端、真实Windows安装及真实官方数据前向检验均未在本次运行环境中完成**。


## 实际验收声明

实际测试与遗留限制详见 `V33_验收实录.md`。五个数学模型家族的精确重构不能证明真实开奖未来有可预测偏差。
