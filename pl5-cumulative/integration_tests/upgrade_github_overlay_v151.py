"""Upgrade a native 五序 frontend, with backups and all-file preflight.

Never modifies arbitrary custom code silently. Use after extracting the v1.5.1 archive.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import shutil
from upgrade_github_overlay_v14 import upgrade as baseline_upgrade

ROOT=Path(__file__).resolve().parent.parent
MARK='// PL5-V1.5.1-EVOLUTION-STATUS'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def upgrade(root:Path):
    # Prior integration, which handles either pristine official code or an existing v12-v15 overlay.
    prior=baseline_upgrade(root)
    wb=root/'src/pages/Workbench.tsx'
    server=root/'server/index.mjs'
    proxy=root/'server/esseProxy.mjs'
    component=root/'src/components/EvolutionStatus.tsx'
    new_proxy=ROOT/'github_overlay/server/esseProxy.mjs'
    new_component=ROOT/'github_overlay/src/components/EvolutionStatus.tsx'
    w=wb.read_text(encoding='utf8'); s=server.read_text(encoding='utf8')
    old_import='import EsseBridge from "../components/EsseBridge";'
    old_panel='          <EsseBridge input={input} onChange={setInput} />'
    old_route='req.url === "/api/esse/health" || req.url === "/api/esse/sculpt"'
    if MARK in w or MARK in s:
        if (MARK in w and MARK in s and component.is_file() and sha(component)==sha(new_component)
                and sha(proxy)==sha(new_proxy)):
            return {'state':'already_applied','baseline':prior}
        raise RuntimeError('V1.5.1整合文件存在不一致或已被修改，请人工检查')
    if w.count(old_import)!=1 or w.count(old_panel)!=1 or s.count(old_route)!=1:
        raise RuntimeError('原有五序插入点不匹配，拒绝修改')
    if component.exists() and sha(component)!=sha(new_component):
        raise RuntimeError('EvolutionStatus与用户自定义组件冲突')
    # Compare the managed proxy against the old overlay rather than overwriting unknown edits.
    baseline=Path(__file__).resolve().parent.parent/'archive/v15_integration_base/server/esseProxy.mjs'
    if not baseline.is_file() or not proxy.is_file() or sha(proxy) not in (sha(baseline),sha(new_proxy)):
        raise RuntimeError('现有Node ESSE代理存在未审查的修改，拒绝覆盖')
    modified_w=w.replace(old_import,MARK+'\nimport EvolutionStatus from "../components/EvolutionStatus";\n'+old_import,1).replace(old_panel,old_panel+'\n          <EvolutionStatus />',1)
    modified_s=s.replace(old_route,old_route+' || req.url === "/api/esse/status"',1)
    anchor='const server = createServer(async (req, res) => {'
    if modified_s.count(anchor)!=1: raise RuntimeError('Node服务插入点不匹配')
    modified_s=modified_s.replace(anchor,MARK+'\n'+anchor,1)
    tasks=[(wb,modified_w.encode('utf8')),(server,modified_s.encode('utf8')),
           (proxy,new_proxy.read_bytes()),(component,new_component.read_bytes())]
    # Backups precede changes, and originals remain untouched on any preflight failure.
    for dest,_ in tasks:
        if dest.exists():
            backup=dest.with_name(dest.name+'.before-v151.bak')
            if backup.exists() and backup.read_bytes()!=dest.read_bytes():
                raise RuntimeError(f'备份冲突: {backup}')
            if not backup.exists():shutil.copy2(dest,backup)
    for dest,data in tasks:
        tmp=dest.with_name(dest.name+'.v151.tmp')
        tmp.write_bytes(data)
        tmp.replace(dest)
    return {'state':'installed','baseline':prior,'files':[str(x.relative_to(root)) for x,_ in tasks]}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--github-root',type=Path,required=True)
    a=p.parse_args();print(upgrade(a.github_root.resolve()))
