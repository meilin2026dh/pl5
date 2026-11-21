"""Read-only V2.0 paper factory page. Safe incremental GitHub overlay install."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import shutil
from upgrade_github_overlay_v19 import upgrade as prior_upgrade
ROOT=Path(__file__).resolve().parent.parent
MARK='// PL5-V2.0-PAPER-FACTORY'
def digest(path:Path):return hashlib.sha256(path.read_bytes()).hexdigest()

def upgrade(root:Path):
    wb=root/'src/pages/Workbench.tsx'
    index=root/'server/index.mjs'
    proxy=root/'server/esseProxy.mjs'
    component=root/'src/components/PaperFactoryV20.tsx'
    old=ROOT/'github_overlay/server/esseProxy_v19.mjs'
    new=ROOT/'github_overlay/server/esseProxy_v20.mjs'
    source=ROOT/'github_overlay/src/components/PaperFactoryV20.tsx'
    if not wb.is_file() or not index.is_file():raise RuntimeError('GitHub五序源码不完整')
    a=wb.read_text('utf8');b=index.read_text('utf8')
    if MARK in a or MARK in b:
        if (MARK in a and MARK in b and component.is_file() and digest(component)==digest(source)
            and proxy.is_file() and digest(proxy)==digest(new) and
            a.count('<PaperFactoryV20 />')==1 and b.count('req.url === "/api/esse/paper-factory"')==1):
            return {'state':'already_applied'}
        raise RuntimeError('发现V2.0部分安装或本地修改，拒绝覆盖')
    old_result=prior_upgrade(root)
    a=wb.read_text('utf8');b=index.read_text('utf8')
    if a.count('          <AbilityLabV19 />')!=1 or b.count('req.url === "/api/esse/ability-lab"')!=1:
        raise RuntimeError('V1.9前端插入点不唯一')
    if not proxy.exists() or digest(proxy)!=digest(old):raise RuntimeError('ESSE代理存在本地修改，拒绝覆盖')
    if component.exists() and digest(component)!=digest(source):raise RuntimeError('新面板存在本地修改，拒绝覆盖')
    changes=[(wb,MARK+'\nimport PaperFactoryV20 from "../components/PaperFactoryV20";\n'
              +a.replace('          <AbilityLabV19 />','          <AbilityLabV19 />\n          <PaperFactoryV20 />',1)),
             (index,MARK+'\n'+b.replace('req.url === "/api/esse/ability-lab"',
                'req.url === "/api/esse/ability-lab" || req.url === "/api/esse/paper-factory"',1)),
             (proxy,new.read_text('utf8')),(component,source.read_text('utf8'))]
    # Validate all backup collisions before first write.
    for path,_ in changes:
        backup=path.with_name(path.name+'.before-v20.bak')
        if backup.exists() and path.exists() and digest(backup)!=digest(path):
            raise RuntimeError('备份冲突，停止覆盖：'+str(backup))
    for path,content in changes:
        path.parent.mkdir(parents=True,exist_ok=True)
        backup=path.with_name(path.name+'.before-v20.bak')
        if path.exists() and not backup.exists():shutil.copy2(path,backup)
        temp=path.with_name(path.name+'.v20.tmp')
        temp.write_bytes(content.encode('utf8'));temp.replace(path)
    return {'state':'installed','prior':old_result,'files':[str(x.relative_to(root)) for x,_ in changes]}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--github-root',type=Path,required=True)
    print(upgrade(p.parse_args().github_root.resolve()))
