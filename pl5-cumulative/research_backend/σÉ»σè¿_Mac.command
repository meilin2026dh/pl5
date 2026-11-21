#!/bin/zsh
# 双击或在终端运行；只在本项目独立虚拟环境安装，不修改系统Python。
set -e
cd "$(dirname "$0")"
if ! command -v uv >/dev/null 2>&1; then
  echo '未找到 uv。请先参考 https://docs.astral.sh/uv/getting-started/installation/ 安装。'
  echo '安装后重新运行本文件。'
  read '?按回车退出...'
  exit 1
fi
uv python install 3.12
uv sync --python 3.12 --extra agent
uv run streamlit run phase2_app.py
