"""Safe additive overlay: leaves user's GitHub working tree intact on conflicts."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import shutil
from upgrade_github_overlay_v151 import upgrade as prior_upgrade

ROOT=Path(__file__).resolve().parent.parent
MARK='// PL5-V1.5.2-FORWARD-EVIDENCE'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def upgrade(root:Path):
    prior=prior_upgrade(root)
    wb=root/'src/pages/Workbench.tsx'
    component=root/'src/components/ForwardEvidence.tsx'
    expected=ROOT/'github_overlay/src/components/ForwardEvidence.tsx'
    text=wb.read_text(encoding='utf8')
    if MARK in text:
        if component.is_file() and sha(component)==sha(expected) and text.count('<ForwardEvidence />')==1:
            return {'state':'already_applied','prior':prior}
        raise RuntimeError('V1.5.2代码有用户修改或不完整，请人工合并')
    if component.exists() and sha(component)!=sha(expected):
        raise RuntimeError('用户已定义ForwardEvidence文件，拒绝覆盖')
    target='          <EvolutionStatus />'
    if text.count(target)!=1:raise RuntimeError('缺少V1.5.1状态面板插入点')
    intro='import ForwardEvidence from "../components/ForwardEvidence";'
    if intro in text:raise RuntimeError('组件部分插入，拒绝自动覆盖')
    changed=MARK+'\n'+intro+'\n'+text
    changed=changed.replace(target,target+'\n          <ForwardEvidence />',1)
    backup=wb.with_name(wb.name+'.before-v152.bak')
    if backup.exists() and sha(backup)!=sha(wb):raise RuntimeError('存在不一致的旧版备份文件')
    if not backup.exists():shutil.copy2(wb,backup)
    wb.write_text(changed,encoding='utf8')
    if not component.exists():shutil.copy2(expected,component)
    return {'state':'installed','prior':prior,'files':['src/pages/Workbench.tsx','src/components/ForwardEvidence.tsx']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--github-root',type=Path,required=True)
    print(upgrade(p.parse_args().github_root.resolve()))
