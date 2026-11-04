"""Add V2.2 read-only research panel to an unmodified V2.1 Five Sequence frontend."""
from __future__ import annotations
import argparse
import hashlib
import shutil
from pathlib import Path
from upgrade_github_overlay_v21 import upgrade as previous

ROOT=Path(__file__).resolve().parent.parent
MARK='// PL5-V2.2-RESEARCH'

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def upgrade(root:Path):
    work=root/'src/pages/Workbench.tsx'
    server=root/'server/index.mjs'
    proxy=root/'server/esseProxy.mjs'
    view=root/'src/components/ResearchCollabV22.tsx'
    component=ROOT/'github_overlay/src/components/ResearchCollabV22.tsx'
    prior=ROOT/'github_overlay/server/esseProxy_v21.mjs'
    fresh=ROOT/'github_overlay/server/esseProxy_v22.mjs'
    if not work.is_file() or not server.is_file():
        raise RuntimeError('缺少完整GitHub五序前端')
    a,b=work.read_text('utf8'),server.read_text('utf8')
    if MARK in a or MARK in b:
        if (MARK in a and MARK in b and a.count('<ResearchCollabV22 />')==1
            and b.count('req.url === "/api/esse/research-v22"')==1
            and view.is_file() and sha(view)==sha(component)
            and proxy.is_file() and sha(proxy)==sha(fresh)):
            return {'state':'already_applied'}
        raise RuntimeError('V2.2安装不完整或存在用户修改，拒绝覆盖')
    # The V2.1 installer checks against its own known release hashes.
    previous(root)
    a,b=work.read_text('utf8'),server.read_text('utf8')
    if a.count('<ResearchCouncilV21 />')!=1 or b.count('req.url === "/api/esse/research-council"')!=1:
        raise RuntimeError('V2.1前端挂载点缺失')
    if not proxy.is_file() or sha(proxy)!=sha(prior):
        raise RuntimeError('代理服务与已发布V2.1基线不符，拒绝覆盖')
    if view.exists() and sha(view)!=sha(component):
        raise RuntimeError('发现用户自定义V2.2组件，拒绝覆盖')
    changes=[
        (work, MARK+'\nimport ResearchCollabV22 from "../components/ResearchCollabV22";\n'
         +a.replace('          <ResearchCouncilV21 />','          <ResearchCouncilV21 />\n          <ResearchCollabV22 />',1)),
        (server,MARK+'\n'+b.replace('req.url === "/api/esse/research-council"',
            'req.url === "/api/esse/research-council" || req.url === "/api/esse/research-v22"',1)),
        (proxy,fresh.read_text('utf8')),
        (view,component.read_text('utf8')),
    ]
    for path,_ in changes:
        backup=path.with_name(path.name+'.before-v22.bak')
        if backup.exists() and path.is_file() and sha(backup)!=sha(path):
            raise RuntimeError('备份文件与待更新文件冲突：'+str(path))
    for path,content in changes:
        path.parent.mkdir(parents=True,exist_ok=True)
        backup=path.with_name(path.name+'.before-v22.bak')
        if path.exists() and not backup.exists():shutil.copy2(path,backup)
        temp=path.with_name(path.name+'.v22.tmp')
        temp.write_bytes(content.encode('utf8'))
        temp.replace(path)
    return {'state':'installed','paths':[str(p.relative_to(root)) for p,_ in changes]}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--github-root',required=True,type=Path)
    print(upgrade(p.parse_args().github_root.resolve()))
