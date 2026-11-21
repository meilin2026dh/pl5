"""Safely add V1.7 read-only research status panel; reject conflicting trees."""
from __future__ import annotations
import argparse
from pathlib import Path
import hashlib
import shutil
from upgrade_github_overlay_v16 import upgrade as prior_upgrade
ROOT=Path(__file__).resolve().parent.parent
MARK='// PL5-V1.7-AUTONOMOUS-OPS'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def upgrade(root):
    prior=prior_upgrade(root)
    wb=root/'src/pages/Workbench.tsx'
    dest=root/'src/components/ResearchOpsV17.tsx'
    src=ROOT/'github_overlay/src/components/ResearchOpsV17.tsx'
    text=wb.read_text('utf8')
    if MARK in text:
        if dest.is_file() and digest(dest)==digest(src) and text.count('<ResearchOpsV17 />')==1:
            return {'state':'already_applied','prior':prior}
        raise RuntimeError('已有V1.7组件被修改或不完整，停止覆盖')
    if dest.exists() and digest(dest)!=digest(src):raise RuntimeError('V1.7组件文件与当前版本不一致')
    anchor='          <ValueCenter />'
    if text.count(anchor)!=1 or 'import ResearchOpsV17 from ' in text:
        raise RuntimeError('未找到唯一V1.6组件插入位置')
    backup=wb.with_name(wb.name+'.before-v17.bak')
    if backup.exists() and digest(backup)!=digest(wb):raise RuntimeError('V1.7备份文件存在冲突')
    updated=MARK+'\nimport ResearchOpsV17 from "../components/ResearchOpsV17";\n'+text
    updated=updated.replace(anchor,anchor+'\n          <ResearchOpsV17 />',1)
    if not backup.exists():shutil.copy2(wb,backup)
    wb.write_text(updated,'utf8')
    if not dest.exists():shutil.copy2(src,dest)
    return {'state':'installed','prior':prior}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--github-root',type=Path,required=True)
    print(upgrade(p.parse_args().github_root.resolve()))
