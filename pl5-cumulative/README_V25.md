# PL5 V2.5 · 自主表示空间发现与协同进化研究版

基于V2.4完整科研后端增加`representation_v25.py`、`representation_registry_v25.py`、`research_v25.py`、Streamlit第13页，原九空间实验室及科研模块保留。

## 一、这次真正增加了什么

- **六类有界数学表示变换**：多位置线性模特征、位对模和、带符号差、三位交互、23选6组合投影模特征、十万域仿射可逆重标记。参数、数学空间、输入输出、算法版本在能力说明书UACP风格研究卡中记录。
- **独立全集去冗余**：针对全部00000—99999计算特征；对“等值重编码”的不同数值标签使用等价分区指纹。可逆重标记保留描述，但不当成新信息增益。
- **相对旧九空间的冗余诊断**：对五种既有基准特征计算条件信息熵与解释比例。该指标用于研究新的结构分桶，不等于预测信息增益。
- **严格时间切分**：只在开发集训练与选模，锁定一个模型后才在历史留出期评价；比较逐期平均对数损失与均匀独立基线。留出数据不能重复挑胜者。
- **自主研究能力库**：每轮根据新的固定种子生成数学变换，通过SQLite持久保存，不重复登记相同分区；不会发布到正式过滤引擎。
- **对照候选**：给出一份研究性Top100和一份等注数随机对照，各组自身均去重；不宣称两个集合有胜率差异。
- **复用V2.4**：原九空间、可逆23选6映射、规则交集、近期反延续及历史回测完全保留。

## 二、数学边界与研究质量

新数学表示空间是原五位号码的确定性函数。即使具有不同的拓扑、属性与分桶，也不会凭编码自动增加公平独立开奖的可预测信息。某类别只包含很少号码，并不意味着类别内某个指定号码下一期的单注概率发生变化。

研究排序采用“以全集精确类别占比为零假设先验 + 历史类别频率”的平滑模型；这只是建模假设，并非官方开奖的真实概率。模型应优先与均匀彩票基线`1/100000`比较，长期前向数据不足时不得注册为具有预测优势的规则。

## 三、Windows安全部署

1. 下载安装ZIP并解压。确认D盘存在后运行`install_to_D_v25.bat`。
2. 后端安装在`D:\pl5\research_backend_v25`，若目录已存在自动停止，避免覆盖。
3. 运行`验证_V25.ps1`进行新旧专项测试，再运行`启动_V25_空间实验室.ps1`。
4. 需要定期扩充**研究算法库**时，显式运行`启用_V25_定时研究.ps1`。它不会替你关闭或覆盖旧版的研究任务，也不会操作GitHub主分支或自动购买。

旧版data、runtime、reports和GitHub五序前端默认不覆盖。当前包没有内置完整GitHub React前端，原先需单独克隆的限制仍然存在。

## 四、命令行

```powershell
cd D:\pl5\research_backend_v25
uv sync --python 3.12 --group dev
uv run python research_v25.py propose --count 24 --seed 20261102 --report reports/proposal_v25.json
uv run python research_v25.py cycle --db D:\pl5\runtime\representation_v25.sqlite --count 24 --report reports/cycle_v25.json
uv run python research_v25.py status --db D:\pl5\runtime\representation_v25.sqlite
uv run python research_v25.py study --history D:\pl5\data\official_history.csv --count 24 --test-periods 30 --report reports/study_v25.json --numbers reports/experimental_and_control.csv
uv run streamlit run "pages/13_自主表示空间发现实验室.py"
```

`--history`必须显式指定已经确认来源的CSV；必须有`number`列且号码恰好五位。支持有`issue`和`date`的记录排序；不要把演示结果冒充官方开奖。

`cycle`不会自动运行历史留出检验以免每六小时重复看旧测试集。要做历史实验，需由研究人员用`study`显式执行，记录历史数据版本与试验次数。

## 五、HTTP接口

`GET /api/esse/spaces-v25/capabilities`返回算子清单与研究库存量；`POST /api/esse/spaces-v25/discover`接收`{"count":8,"seed":20261102}`生成工程候选；另可传`history`五位号码列表和`test_periods`触发一次历史留出实验。只监听127.0.0.1的科研服务，不接受远程可执行代码，不发布正式选号规则。

## 六、验收边界

新模块可以自行运行、生成研究档案、对全部10万注执行数学运算、导出候选与回测。**尚未在用户Windows D盘实机部署、没有自动导入最新官方开奖、未对GitHub前端完成原生页面集成，也未证明任何预测提升。**
