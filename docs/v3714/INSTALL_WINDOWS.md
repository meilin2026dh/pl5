# Windows D:\\pl5 V3.7.14 setup and retest (not yet executed)

Keep a backup of the existing D:\\pl5 project. Unzip the full research package into a separate directory, e.g. D:\\pl5-v3714.

From the extracted `research_backend` folder in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest tests\test_high_throughput_v3714.py tests\test_high_throughput_benchmark_v3714.py -q
.\.venv\Scripts\python.exe benchmark_high_throughput_v3714.py --output ..\docs\v3714\benchmark_windows.json --repeats 20 --seed 3714
```

Evaluate cold-index build time separately from warm-query speed. Do not confuse Linux measured performance with Windows acceptance. Cache invalidation is required when underlying historical data or custom indicators change.
