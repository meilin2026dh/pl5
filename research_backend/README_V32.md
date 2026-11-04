# PL5 V3.2 —— 算子类别假设自生成与结构证伪

**升级来源：** V3.1 完整工程源码。新增模块在 `research_backend/pailie5/category_hypotheses_v32.py`，保留已有 BCSE、HDSE、AAN、ESSE 及 V3.1 商类/周期轨道等历史功能。

## 本次实际新增

V3.1 只能检验 `row_column_quotient`、`cyclic_difference`、`cyclic_sum` 三类。V3.2 不再只查这三种：系统从输入运算表的行归一化轮廓、模映射残差和局部反例中生成数学类别候选，逐个进行完整 100 格证明，再与 V3.1 最短表达作成本比较。新增：

- **分段轨道**（`piecewise_orbit`）：将行轨道轮廓自动聚类为 2—3 个状态，学习状态编号与每状态的 10 元素轨道函数；可理解为小规模、行状态驱动的有限状态输出模型。
- **广义模轨道**（`affine_orbit`）：从 81 组 `(u,v)` 中搜索 `g((u·a+v·b) mod 10)`，轨道函数 `g` 由数据自动归纳，必须全域精确成立。
- **稀疏例外轨道**（`sparse_orbit_exceptions`）：自动发现主轨道规则及最多 6 个残差点，逐格修复，超出描述复杂度门槛则拒绝。

这三类是**受控候选类别发现**，不是完全自由地发明新数学公理或从任意数据中自动形成无限种表达语言。系统最多为每种类别保留一条当前最短可证明的数学能力，其余候选进入拒绝计数/诊断记录。

## 验证规则

1. 每种新定义必须与给定的10×10原始表全部100格一致；NumPy与Python标量实现分别核验。
2. 与V3.1最短描述相比必须**严格更短**，才算本轮新增的数学能力；否则明确拒绝，避免旧类重包装。
3. 固定编码成本只是**MDL式描述长度代理**，不是压缩文件实际位数，也不是赔率或中奖概率。
4. 算法定义、数据指纹、证据与来源写入独立SQLite科研能力库；不覆盖已登记的不同能力。
5. 所有新能力 `research_only`，可在 AAN受控JSON调用链使用、生成 ESSE研究掩码，但不自动成为正式彩票过滤规则。
6. 在以历史数据诱导V2.9运算表的流程中，最后110条记录始终不参与拟合、选择或算子发明；这**不等于**已经验证未来预测优势。

## 演示实验

| 合成数学表 | V3.1最短代理 | V3.2新类 | V3.2代理 | 全域结果 |
|---|---:|---|---:|---|
| 2状态分段轨道 | 200bit | piecewise_orbit | 75bit | 100/100一致 |
| 广义模轨道 | 194bit | affine_orbit | 52bit | 100/100一致 |
| 循环差+2处人为扰动 | 200bit | sparse_orbit_exceptions | 70bit | 100/100一致 |
| 随机无结构4类别运算表 | 200bit | 无 | — | 正确拒绝 |

**上述数字仅针对数学合成运算表，全部与彩票真实开奖结果无关。** 复杂结构被更简洁表达，不说明下一期可预测；公平独立开奖下，事先确定的100注精确覆盖仍为0.1%。

## Windows安装

解压全部文件，双击 `install_to_D_v32.bat`，将新版本复制到 `D:\pl5\research_backend_v32`。原始 `D:\pl5\data`、`runtime`、GitHub前端和旧版本目录不会覆盖。脚本不自动安装为后台服务。

在 PowerShell 中：

```powershell
cd D:\pl5\research_backend_v32
uv sync --python 3.12 --group dev
uv run python -m pytest -q tests/test_category_hypotheses_v32.py
uv run python research_v32.py demo
uv run streamlit run "pages/20_数学类别假设自进化.py"
```

可运行 `验证_V32.ps1` 做本机关键测试与演示，`验证_V32.ps1 -Full` 执行完整回归。

使用已核实的官方历史CSV：

```powershell
uv run python research_v32.py study --history "D:\pl5\data\official.csv" --maximum 8
```

自定义运算表需为**10行×10列**、恰好3或4个连续输出类别0..k−1：

```powershell
uv run python research_v32.py table --table-json "D:\pl5\data\operator.json"
```

通过 `启用_V32_定时研究.ps1` 可**手动**登记每天00:15、06:15、12:15、18:15运行的Windows任务；默认仅合成数学研究，指定`-HistoryCsv`时才使用给定CSV。应先手动停用旧版任务。用户电脑必须开机并拥有必要的运行环境；尚未完成本机Windows验收。

## 完整性与数据边界

所有的官方历史数据都应来自可独立核验的中国体育彩票官方渠道。V3.2默认不联网检索论文、不自动下载官方历史、不调用付费模型，不意味着可以自行持续创造任意数学类型；这里只扩充了**可自动提出并证伪的受限类别家族**。若要扩展无限开放式创造，需要另行建设搜索语言生成与形式证明系统。未来彩票开奖的预测价值仍需长周期、事先封存的独立验证。
