"""Safe GitHub overlay install/upgrade, accepting only known V1.2/V1.3 files.

No git pull/reset, no overwrite of unknown changes. Creates backups before writes.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import shutil
from apply_github_overlay import apply

ROOT=Path(__file__).resolve().parent.parent
OVERLAY=ROOT/'github_overlay'
PREVIOUS={
  'src/components/EsseBridge.tsx':{
      '915b26b11ca3378f25dca50f8f6fcada073bdf665fa660793d34667ee213d584',
      '4cd705c6ccec89802641bdd3310899d8627c3f646cdad2aeeb68a530862232dc'},
  'src/workers/esse.worker.ts':{
      '6f5c52c6332c7cb6371a5cf7f178087babc8e93fe6fedcc9ab384f5fb1e1ae23',
      '529e0f8c496bc2678bef6515bb99439ade39d488f381076af0dc64a79e9e387c'},
  'server/esseProxy.mjs':{'af94e550a87d5b8b7bd86fa44363c5e84cf49a086f9dc6dd63ad9969cd3f0454'},
  'tests/esse-integration.test.ts':{'bd1c7dc269ffdbf971ec72395a773674dadd757c524b5183197ab2e760e85fcf'},
}

def digest(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def upgrade(root:Path):
    wb=root/'src/pages/Workbench.tsx';server=root/'server/index.mjs'
    if not wb.is_file() or not server.is_file():
        raise RuntimeError('必须是完整五序GitHub源码根目录')
    wbmark='// PL5-V1.2-ESSE-INTEGRATION' in wb.read_text(encoding='utf8')
    servermark='// PL5-V1.2-ESSE-INTEGRATION' in server.read_text(encoding='utf8')
    if wbmark!=servermark:
        raise RuntimeError('GitHub工作台和Node代理的ESSE标记不一致；拒绝安装')
    if not wbmark:
        return {'mode':'new','result':apply(root)}
    if '<EsseBridge input={input} onChange={setInput} />' not in wb.read_text(encoding='utf8'):
        raise RuntimeError('ESSE工作台插入点被修改，拒绝覆盖')
    if 'await handleEsseProxy(req, res)' not in server.read_text(encoding='utf8'):
        raise RuntimeError('ESSE Node代理插入点被修改，拒绝覆盖')
    # Validate *all* files before changing any, avoiding half-upgraded custom overlays.
    changes=[]
    for rel,allowed in PREVIOUS.items():
        target=root/rel
        source=OVERLAY/rel
        if not target.is_file():raise RuntimeError(f'缺少受管理的接入文件：{rel}')
        h=digest(target)
        if h not in allowed and h!=digest(source):
            raise RuntimeError(f'用户自定义文件被检测到，拒绝覆盖：{rel}')
        if h!=digest(source):changes.append(rel)
    for rel in changes:
        dest=root/rel
        backup=dest.with_name(dest.name+'.v13-before-v14.bak')
        if not backup.exists():shutil.copy2(dest,backup)
        shutil.copy2(OVERLAY/rel,dest)
    return {'mode':'upgrade-v12-or-v13','changed':changes}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--github-root',required=True,type=Path)
    a=p.parse_args();print(upgrade(a.github_root.resolve()))
