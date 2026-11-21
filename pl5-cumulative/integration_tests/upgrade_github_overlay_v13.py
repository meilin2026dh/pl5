"""Install V1.3 ESSE into actual 五序 source, safely upgrading V1.2 patches.

No Git fetch/pull and no overwrite of unknown user edits. Never changes main branch.
"""
from __future__ import annotations
import argparse, hashlib, shutil
from pathlib import Path
from apply_github_overlay import apply as install_clean

HERE=Path(__file__).resolve().parent
OVERLAY=HERE.parent/'github_overlay'
V12_SHA256={
  'server/esseProxy.mjs':'af94e550a87d5b8b7bd86fa44363c5e84cf49a086f9dc6dd63ad9969cd3f0454',
  'tests/esse-integration.test.ts':'bd1c7dc269ffdbf971ec72395a773674dadd757c524b5183197ab2e760e85fcf',
  'src/components/EsseBridge.tsx':'915b26b11ca3378f25dca50f8f6fcada073bdf665fa660793d34667ee213d584',
  'src/workers/esse.worker.ts':'6f5c52c6332c7cb6371a5cf7f178087babc8e93fe6fedcc9ab384f5fb1e1ae23',
}
def digest(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def upgrade(root:Path)->dict:
    wb=root/'src/pages/Workbench.tsx'
    server=root/'server/index.mjs'
    if not wb.is_file() or not server.is_file():
        raise RuntimeError('必须指定五序PL5原始GitHub前端根目录')
    old='// PL5-V1.2-ESSE-INTEGRATION' in wb.read_text(encoding='utf8')
    if old != ('// PL5-V1.2-ESSE-INTEGRATION' in server.read_text(encoding='utf8')):
        raise RuntimeError('V1.2旧版补丁状态不一致，拒绝改动')
    if not old:
        return {'mode':'new','result':install_clean(root)}
    changes=[]
    for rel,sha_old in V12_SHA256.items():
        target=root/rel;src=OVERLAY/rel
        if not target.is_file():raise RuntimeError(f'缺少原V1.2集成文件:{rel}')
        existing=digest(target);new=digest(src)
        if existing not in (sha_old,new):
            raise RuntimeError(f'{rel}含用户修改，拒绝覆盖；请手动审查差异')
        if existing==new:continue
        backup=target.with_name(target.name+'.v12-before-v13.bak')
        if not backup.exists():shutil.copy2(target,backup)
        shutil.copy2(src,target)
        changes.append(rel)
    return {'mode':'upgrade-v12','changed':changes}
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--github-root',type=Path,required=True)
    args=parser.parse_args()
    print(upgrade(args.github_root.resolve()))
