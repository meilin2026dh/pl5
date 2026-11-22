"""Apply frontend overlay to a checked-out meilin2026dh/pl5 clone.

Only two existing files are edited, with exact anchors and a .v12.bak backup.
The script never overwrites any user data, plans or history cache.
"""
from __future__ import annotations
import argparse
import shutil
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent / "github_overlay"
MARKER = "// PL5-V1.2-ESSE-INTEGRATION"

def update(path: Path, find: str, replacement: str):
    original = path.read_text(encoding="utf-8")
    if MARKER in original:
        return "already_applied"
    if original.count(find) != 1:
        raise RuntimeError(f"原生GitHub代码锚点变化，请人工核对，不自动修改: {path}")
    backup = path.with_name(path.name+".v12.bak")
    if not backup.exists(): backup.write_text(original,encoding="utf-8")
    path.write_text(original.replace(find,replacement,1),encoding="utf-8")
    return "patched"

def apply(root: Path):
    if not (root/"src/pages/Workbench.tsx").is_file() or not (root/"server/index.mjs").is_file():
        raise RuntimeError("目标必须是GitHub五序PL5源码根目录（非Python旧项目根目录）")
    for folder in ["src/components","src/workers","tests","server"]:
        (root/folder).mkdir(parents=True,exist_ok=True)
        for source in (PAYLOAD/folder).glob("*"):
            if not source.is_file():continue
            dest=root/folder/source.name
            if dest.exists() and dest.read_bytes()!=source.read_bytes():
                raise RuntimeError(f"已有同名但内容不同的文件: {dest}，请先人工合并")
            if not dest.exists():shutil.copy2(source,dest)
    wb=root/"src/pages/Workbench.tsx"
    anchor='import DiscoveryLab from "../components/DiscoveryLab";'
    update(wb,anchor,f'{MARKER}\nimport EsseBridge from "../components/EsseBridge";\n'+anchor)
    # Insertion uses a separate marker so the script can remain idempotent.
    original=wb.read_text(encoding="utf-8")
    target="          <ConditionLab input={input} onChange={setInput} />"
    addition='          <EsseBridge input={input} onChange={setInput} />\n'+target
    if '<EsseBridge ' not in original:
        if original.count(target)!=1:raise RuntimeError("Workbench插入位置已发生变更")
        wb.write_text(original.replace(target,addition,1),encoding="utf-8")
    server=root/"server/index.mjs"
    anchor='import { createServer } from "node:http";'
    update(server,anchor,f'{MARKER}\nimport {{ handleEsseProxy }} from "./esseProxy.mjs";\n'+anchor)
    original=server.read_text(encoding="utf-8")
    anchor='const server = createServer(async (req, res) => {'
    insertion='const server = createServer(async (req, res) => {\n  if (req.url === "/api/esse/health" || req.url === "/api/esse/sculpt") {\n    await handleEsseProxy(req, res);\n    return;\n  }'
    if 'await handleEsseProxy(req, res)' not in original:
        if original.count(anchor)!=1: raise RuntimeError("Node API插入位置已发生变更")
        server.write_text(original.replace(anchor,insertion,1),encoding="utf-8")
    return {"changed":["src/pages/Workbench.tsx","server/index.mjs"],
            "added":["src/components/EsseBridge.tsx","src/workers/esse.worker.ts","server/esseProxy.mjs","tests/esse-integration.test.ts"]}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--github-root",required=True,type=Path)
    args=p.parse_args()
    print(apply(args.github_root.resolve()))
