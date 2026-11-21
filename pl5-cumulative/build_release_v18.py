from __future__ import annotations
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parent
DEST=ROOT.parent/'PL5_V1.8_算法能力网络与自主协同创新_完整部署包.zip'
SKIP={'.pytest_cache','__pycache__','.venv','node_modules','.git','runtime'}
files=[]
for p in ROOT.rglob('*'):
    if not p.is_file() or any(x in SKIP for x in p.relative_to(ROOT).parts) or p.suffix in ('.pyc','.pyo'):
        continue
    if p.name in ('build_release_v18.py','V18_SHA256_manifest.json'):
        continue
    files.append(p)
files.sort(key=lambda x:x.relative_to(ROOT).as_posix())
manifest={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(ROOT/'V18_SHA256_manifest.json').write_text(json.dumps({'format':'pl5-release-v18','file_count':len(files),'files':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
files.append(ROOT/'V18_SHA256_manifest.json')
files.append(ROOT/'build_release_v18.py')
with zipfile.ZipFile(DEST,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
    for p in files:z.write(p,arcname=p.relative_to(ROOT).as_posix())
print(DEST,DEST.stat().st_size,len(files))
