# Windows / D:\pl5 安装与复验（仅操作说明；本会话未在你的Windows电脑上执行）

1. 先备份 `D:\pl5` 及数据、配置文件。不要直接把研究包覆盖到现有主仓库的工作目录。
2. 解压 `PL5_V3714_Full.zip` 到独立目录，例如 `D:\pl5-v3714`；源码在其 `research_backend` 子目录。
3. 安装 Python 3.12 并准备项目依赖（使用单独虚拟环境，勿改动系统Python）。
4. 在 `research_backend` 目录依次执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest tests\test_high_throughput_v3714.py tests\test_high_throughput_benchmark_v3714.py -q
.\.venv\Scripts\python.exe benchmark_high_throughput_v3714.py --output ..\docs\v3714\benchmark_windows.json --repeats 20 --seed 3714
```

5. 与 `docs/v3714/benchmark.json` 的 Linux 实测做对照，不能把Linux的速度数字当成Windows验收值。
6. 将新模块引入主平台时，只以它的 `ExactFilterEngine` 做纯工程加速；不要把排名、候选生成的含义改成彩票预测。
7. 如果旧规则依赖最新开奖数据，更新数据后必须调用 `invalidate('indicator:<name>')` 或重新注册规则，防止查询旧缓存。

注意：当前研究包是累计科研源码快照，不等于本地 `D:\pl5` 的实际Git项目状态；本会话没有自动安装、覆盖或推送本地文件。
