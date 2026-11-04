"""Apply V1.8 additive network panel to the audited V1.7 GitHub overlay."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import shutil
from upgrade_github_overlay_v17 import upgrade as prior_upgrade

ROOT=Path(__file__).resolve().parent.parent
MARK='// PL5-V1.8-ALGORITHM-ABILITY-NETWORK'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def upgrade(root:Path):
    wb=root/'src/pages/Workbench.tsx'
    server=root/'server/index.mjs'
    proxy=root/'server/esseProxy.mjs'
    component=root/'src/components/CapabilityNetworkV18.tsx'
    replacement=ROOT/'github_overlay/server/esseProxy_v18.mjs'
    source=ROOT/'github_overlay/src/components/CapabilityNetworkV18.tsx'
    old_proxy=ROOT/'archive/v17_proxy/server/esseProxy.mjs'
    w=wb.read_text('utf8');s=server.read_text('utf8')
    if MARK in w or MARK in s:
        if (MARK in w and MARK in s and component.is_file() and digest(component)==digest(source)
            and proxy.is_file() and digest(proxy)==digest(replacement)
            and w.count('<CapabilityNetworkV18 />')==1
            and s.count('req.url === "/api/esse/capabilities"')==1):
            return {'state':'already_applied','prior':'previously_verified'}
        raise RuntimeError('V1.8存在不完整或自行修改的文件，拒绝覆盖')
    prior=prior_upgrade(root)
    w=wb.read_text('utf8');s=server.read_text('utf8')
    if w.count('          <ResearchOpsV17 />')!=1:
        raise RuntimeError('缺少V1.7工作台唯一插入点')
    old='req.url === "/api/esse/status"'
    if s.count(old)!=1:
        raise RuntimeError('缺少唯一科研状态路由')
    if not proxy.is_file() or digest(proxy)!=digest(old_proxy):
        raise RuntimeError('Node科研代理存在未审查修改，拒绝覆盖')
    if component.exists() and digest(component)!=digest(source):
        raise RuntimeError('能力网络组件存在冲突')
    neww=MARK+'\nimport CapabilityNetworkV18 from "../components/CapabilityNetworkV18";\n'+w
    neww=neww.replace('          <ResearchOpsV17 />','          <ResearchOpsV17 />\n          <CapabilityNetworkV18 />',1)
    news=s.replace(old,old+' || req.url === "/api/esse/capabilities"',1)
    news=MARK+'\n'+news
    tasks=[(wb,neww.encode()),(server,news.encode()),(proxy,replacement.read_bytes()),(component,source.read_bytes())]
    for dest,raw in tasks:
        if dest.exists():
            backup=dest.with_name(dest.name+'.before-v18.bak')
            if backup.exists() and backup.read_bytes()!=dest.read_bytes():
                raise RuntimeError('备份冲突: '+str(backup))
    for dest,raw in tasks:
        if dest.exists():
            backup=dest.with_name(dest.name+'.before-v18.bak')
            if not backup.exists():shutil.copy2(dest,backup)
        temp=dest.with_name(dest.name+'.v18.tmp')
        temp.write_bytes(raw);temp.replace(dest)
    return {'state':'installed','prior':prior,'files':[str(x.relative_to(root)) for x,_ in tasks]}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--github-root',required=True,type=Path)
    print(upgrade(p.parse_args().github_root.resolve()))
