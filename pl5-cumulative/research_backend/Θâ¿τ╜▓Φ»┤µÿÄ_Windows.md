# PL5 V0.4 · Windows D盘安全升级和启动

## 运行方式

下载 `PL5_V0.4_多空间竞争与映射稳健性_完整部署包.zip`，解压到临时文件夹，目录中应有：

- `pl5/`：完整项目文件夹；
- `install_to_D_v04.ps1`：安全升级脚本；
- `install_to_D_v04.bat`：双击安装入口。

双击 `install_to_D_v04.bat`，或者在解压目录中执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_to_D_v04.ps1
```

安装脚本只会使用 `D:\pl5`，D盘不存在时立即中止。若目录已经存在，将在 `D:\pl5_backups\backup_before_V04_日期时间` 备份**将被覆盖的源码文件**；不覆盖或删除 `D:\pl5\data`、`D:\pl5\runtime`、`D:\pl5\.venv`、`D:\pl5\archive`。如果备份失败，会在正式复制源码前中止。

Python程序不能从当前会话直接写入你的Windows D盘；上述步骤需要在你的电脑实际执行。

## 启动及测试

在PowerShell中：

```powershell
cd D:\pl5
uv python install 3.12
uv sync --python 3.12 --extra agent --group dev
uv run pytest -q
uv run streamlit run phase2_app.py
```

在Streamlit左侧页面导航选择 `04 多空间竞争与稳健性`。

命令行示范：

```powershell
uv run python multispace_cli.py --csv data\synthetic_demo.csv --demo --out runtime\v04_demo
```

导出十万注排名CSV、规则竞争CSV、滚动回测和映射稳健性JSON。演示数据是伪随机生成的，不是彩票官方历史数据。正式使用请上传从中国体彩官方渠道核验的开奖CSV。

## 回滚

若更新后功能异常，可将 `D:\pl5_backups\backup_before_V04_...` 中相应的原文件复制回 `D:\pl5` 对应路径。升级前先退出正在运行的Streamlit服务，避免Windows文件占用。由于旧版本没有新的模块，回滚时需要同时停用新增的V0.4页面，必要时用之前完整版本包恢复程序源码；不要删除数据和数据库。

## 验收边界

当前执行环境已验证Python核心代码、完整命令行演示、自动化测试；**未验证实际Windows PowerShell安装、Streamlit浏览器运行以及官方真实开奖数据获取**。这些步骤属于D盘本机验收。


## V0.5增补：自主科研任务与下一期验证

本升级包增加 `autoresearch/`、`research_cli.py`、`pages/05_自主科研智能体.py`。
默认不启用后台联网任务；用户显式执行 `启用_定时科研.ps1` 后每6小时巡检。
使用已核验的官方CSV运行 `research_cli.py freeze` 将本期候选集在开奖前封存；开奖后使用 `research_cli.py settle` 追加核验结果；不得用历史回测冒充前向10期验证。
详细操作见 `README_V05.md`。
