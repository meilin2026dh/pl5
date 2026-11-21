# PL5 V3.7.10 — 由失败反例驱动的数学原语组合研究

本版本以 `PL5_V379_Full.zip` 为精确不变基线，新增研究模块，不覆盖 V1.x—V3.7.9 历史源码与研究记录。属于**受限数学科研预览版**，不是生产彩票预测/过滤服务。

## 新增文件
- `research_backend/pailie5/generated_primitives_v3710.py`：训练矛盾见证、受限数学语法自动组合、保守冻结与弃权。
- `research_backend/pailie5/generated_study_v3710.py`：带随机负对照、训练噪声和规律漂移的登记实验协议。
- `research_backend/research_generated_v3710.py`：可复现命令行科研实验入口。
- `research_backend/tests/test_generated_primitives_v3710.py`、`test_generated_study_v3710.py`：新增专项与防泄漏回归测试。
- `docs/v3710`：登记协议、实际结果、复现摘要、压力测试、验证报告。

## Windows 测试（须先安装项目开发依赖）

在项目根目录（建议先备份并用新文件夹）运行：

```powershell
cd D:\pl5\research_backend
py -3.12 -m pytest -q tests\test_generated_primitives_v3710.py tests\test_generated_study_v3710.py
py -3.12 research_generated_v3710.py --output ..\runs\v3710_demo --seeds 9811 9812
```

`research_generated_v3710.py` 只运行指定的有限批次，**不启动任何持续服务**。原压缩包保持不变。更安全的做法是先在隔离目录解压完整包测试，而不是覆盖生产环境。

本引擎生成的是已知小型数学运算的**程序组合**，不意味着开放式数学公理发明；对随机数据的弃权也不能证明真实彩票开奖存在可利用规律。`production_enabled=false`，`predictive_advantage=NOT_ESTABLISHED`。

历史平台 `research_backend/pyproject.toml` 的版本号仍是3.7.6；V3.7.10是研究模块版本，尚未进行正式平台级版本发布，也未在Windows实机部署或同步GitHub。
