"""Safe, idempotent V2.1 read-only panel overlay over pinned GitHub code."""
from __future__ import annotations
import argparse,hashlib,shutil
from pathlib import Path
from upgrade_github_overlay_v20 import upgrade as v20
ROOT=Path(__file__).resolve().parent.parent
MARK='// PL5-V2.1-COUNCIL'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def upgrade(root:Path):
    wb=root/'src/pages/Workbench.tsx';server=root/'server/index.mjs'
    proxy=root/'server/esseProxy.mjs';component=root/'src/components/ResearchCouncilV21.tsx'
    prior=ROOT/'github_overlay/server/esseProxy_v20.mjs'
    new=ROOT/'github_overlay/server/esseProxy_v21.mjs'
    source=ROOT/'github_overlay/src/components/ResearchCouncilV21.tsx'
    if not wb.is_file() or not server.is_file():raise RuntimeError('未找到GitHub五序主文件')
    a=wb.read_text('utf8');b=server.read_text('utf8')
    if MARK in a or MARK in b:
        if (MARK in a and MARK in b and component.exists() and sha(component)==sha(source)
            and proxy.exists() and sha(proxy)==sha(new) and a.count('<ResearchCouncilV21 />')==1
            and b.count('req.url === "/api/esse/research-council"')==1):
            return {'state':'already_applied'}
        raise RuntimeError('V2.1部分更新或本地修改，拒绝覆盖')
    result=v20(root)
    a=wb.read_text('utf8');b=server.read_text('utf8')
    if a.count('          <PaperFactoryV20 />')!=1 or b.count('req.url === "/api/esse/paper-factory"')!=1:
        raise RuntimeError('V2.0前端挂载点数量错误')
    if not proxy.exists() or sha(proxy)!=sha(prior):
        raise RuntimeError('检测到Node代理被修改；不覆盖本地代码')
    if component.exists() and sha(component)!=sha(source):
        raise RuntimeError('V2.1组件已存在且与发布版本冲突')
    changes=[(wb,MARK+'\nimport ResearchCouncilV21 from "../components/ResearchCouncilV21";\n'
            +a.replace('          <PaperFactoryV20 />','          <PaperFactoryV20 />\n          <ResearchCouncilV21 />',1)),
             (server,MARK+'\n'+b.replace('req.url === "/api/esse/paper-factory"',
                 'req.url === "/api/esse/paper-factory" || req.url === "/api/esse/research-council"',1)),
             (proxy,new.read_text('utf8')),(component,source.read_text('utf8'))]
    for p,_ in changes:
        backup=p.with_name(p.name+'.before-v21.bak')
        if backup.exists() and p.exists() and sha(backup)!=sha(p):
            raise RuntimeError('备份冲突：'+str(p))
    for p,content in changes:
        p.parent.mkdir(parents=True,exist_ok=True)
        backup=p.with_name(p.name+'.before-v21.bak')
        if p.exists() and not backup.exists():shutil.copy2(p,backup)
        tmp=p.with_name(p.name+'.v21.tmp');tmp.write_text(content,'utf8');tmp.replace(p)
    return {'state':'installed','prior':result,'files':[str(p.relative_to(root)) for p,_ in changes]}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--github-root',type=Path,required=True)
    print(upgrade(a.parse_args().github_root.resolve()))
