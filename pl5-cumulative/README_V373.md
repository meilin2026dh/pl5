# PL5 V3.7.3 累计科研交付

本包包含V3.7.2累计源码及全部历史资料，并增量加入等预算机制消融研究。旧775个文件未改写。新增科研交付编号是3.7.3；原Python项目包元数据仍保留历史3.7.2，避免篡改旧版本验收记录。这里不是重新开发独立平台，也不是正式彩票预测产品。

## 从哪里开始

完整报告：`docs/v373/RESEARCH_REPORT.md`；机器验收：`docs/v373/VERIFICATION.json`；实验协议与480条结果：`docs/v373/benchmark/`。
新增模块：`research_backend/pailie5/ablation_search_v373.py`、`ablation_benchmark_v373.py`、`ablation_statistics_v373.py`；入口：`research_backend/research_v373.py`。

在Python 3.12及以上、满足既有pyproject.toml依赖的环境中：

```powershell
cd research_backend
python research_v373.py --output ../runs/v373_local --budget 2500
python -m pytest -q
```

运行目录必须是新目录。重跑一次生成480条记录；不要把相同种子的重跑当成新增样本。全部是合成运算表，不是开奖数据；生产过滤始终禁用。

增量补丁只适用于V3.7.2累计包根目录，不能直接覆盖缺少该基线的更早版本；优先使用累计包。未执行GitHub上传、Windows部署或完整React构建。
