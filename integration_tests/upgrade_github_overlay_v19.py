"""Add V1.9 read-only research panel; fail on local edits, retain safe backups."""
from __future__ import annotations
import argparse,hashlib,shutil
from pathlib import Path
from upgrade_github_overlay_v18 import upgrade as upgrade_prior
ROOT=Path(__file__).resolve().parent.parent
MARK='// PL5-V1.9-GOAL-DIRECTED-ABILITY-LAB'
def digest(p:Path):return hashlib.sha256(p.read_bytes()).hexdigest()

def upgrade(root:Path):
    wb=root/'src/pages/Workbench.tsx'
    server=root/'server/index.mjs'
    proxy=root/'server/esseProxy.mjs'
    component=root/'src/components/AbilityLabV19.tsx'
    old=ROOT/'github_overlay/server/esseProxy_v18.mjs'
    new=ROOT/'github_overlay/server/esseProxy_v19.mjs'
    src=ROOT/'github_overlay/src/components/AbilityLabV19.tsx'
    if not wb.exists() or not server.exists():raise RuntimeError('GitHub五序源码不完整')
    w=wb.read_text('utf8');s=server.read_text('utf8')
    if MARK in w or MARK in s:
        if (MARK in w and MARK in s and component.exists() and digest(component)==digest(src)
            and proxy.exists() and digest(proxy)==digest(new) and w.count('<AbilityLabV19 />')==1
            and s.count('req.url === "/api/esse/ability-lab"')==1):
            return {'state':'already_applied'}
        raise RuntimeError('发现V1.9文件修改或不完整安装，拒绝覆盖')
    result=upgrade_prior(root)
    w=wb.read_text('utf8');s=server.read_text('utf8')
    if w.count('          <CapabilityNetworkV18 />')!=1:raise RuntimeError('V1.8面板插入点不唯一')
    if s.count('req.url === "/api/esse/capabilities"')!=1:raise RuntimeError('V1.8 API路由缺失')
    if not proxy.exists() or digest(proxy)!=digest(old):raise RuntimeError('GitHub代理被修改，拒绝覆盖')
    if component.exists() and digest(component)!=digest(src):raise RuntimeError('V1.9面板存在本地修改')
    changes=[(wb,MARK+'\nimport AbilityLabV19 from "../components/AbilityLabV19";\n'+w.replace(
        '          <CapabilityNetworkV18 />','          <CapabilityNetworkV18 />\n          <AbilityLabV19 />',1)),
        (server,MARK+'\n'+s.replace('req.url === "/api/esse/capabilities"',
            'req.url === "/api/esse/capabilities" || req.url === "/api/esse/ability-lab"',1)),
        (proxy,new.read_text('utf8')),(component,src.read_text('utf8'))]
    for dst,_ in changes:
        if dst.exists():
            backup=dst.with_name(dst.name+'.before-v19.bak')
            if backup.exists() and digest(backup)!=digest(dst):raise RuntimeError('已存在不同的V1.9备份：'+str(backup))
    for dst,content in changes:
        dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists():
            backup=dst.with_name(dst.name+'.before-v19.bak')
            if not backup.exists():shutil.copy2(dst,backup)
        tmp=dst.with_name(dst.name+'.v19.tmp');tmp.write_text(content,'utf8');tmp.replace(dst)
    return {'state':'installed','prior':result,'files':[str(p.relative_to(root)) for p,_ in changes]}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--github-root',type=Path,required=True)
    print(upgrade(p.parse_args().github_root.resolve()))
