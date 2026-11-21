@echo off
chcp 65001 >nul
cd /d D:\pl5
if not exist .venv\Scripts\python.exe (
 echo 请先安装：uv sync --python 3.12 --extra agent --group dev
 pause
 exit /b 1
)
.venv\Scripts\python.exe research_cli.py cycle
pause
