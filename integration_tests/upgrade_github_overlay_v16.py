"""Safely append V1.6 ValueCenter to an already versioned or pristine GitHub tree."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import shutil
from upgrade_github_overlay_v152 import upgrade as prior_upgrade

ROOT=Path(__file__).resolve().parent.parent
MARK='// PL5-V1.6-RESEARCH-VALUE'

def hash_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def upgrade(root:Path):
    base=prior_upgrade(root)
    wb=root/'src/pages/Workbench.tsx'
    component=root/'src/components/ValueCenter.tsx'
    expected=ROOT/'github_overlay/src/components/ValueCenter.tsx'
    content=wb.read_text(encoding='utf8')
    if MARK in content:
        if component.is_file() and hash_file(component)==hash_file(expected) and content.count('<ValueCenter />')==1:
            return {'state':'already_applied','prior':base}
        raise RuntimeError('V1.6文件存在不完整或本机改动，拒绝覆盖')
    if component.exists() and hash_file(component)!=hash_file(expected):
        raise RuntimeError('现有ValueCenter文件与升级包不同，拒绝覆盖')
    anchor='          <ForwardEvidence />'
    if content.count(anchor)!=1:
        raise RuntimeError('未找到V1.5.2前向证据插入点')
    if 'import ValueCenter ' in content:
        raise RuntimeError('V1.6导入语句已存在但版本标记缺失，拒绝覆盖')
    updated=MARK+'\n'+'import ValueCenter from "../components/ValueCenter";\n'+content
    updated=updated.replace(anchor,anchor+'\n          <ValueCenter />',1)
    backup=wb.with_name(wb.name+'.before-v16.bak')
    if backup.exists() and hash_file(backup)!=hash_file(wb):
        raise RuntimeError('旧版V1.6备份文件不匹配，拒绝覆盖')
    if not backup.exists():shutil.copy2(wb,backup)
    wb.write_text(updated,encoding='utf8')
    if not component.exists():shutil.copy2(expected,component)
    return {'state':'installed','prior':base,
            'files':['src/pages/Workbench.tsx','src/components/ValueCenter.tsx']}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--github-root',type=Path,required=True)
    print(upgrade(parser.parse_args().github_root.resolve()))
