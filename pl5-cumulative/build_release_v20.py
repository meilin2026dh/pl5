from __future__ import annotations
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'PL5_V2.0_论文算法创造与隔离复现_完整部署包.zip'
PREFIX=ROOT.name
SKIP_DIRS={'.pytest_cache','__pycache__','.git','node_modules','.venv','.mypy_cache','.ruff_cache'}
SKIP_SUFFIX={'.pyc','.pyo','.db','.sqlite','.log','.tmp'}
EXCLUDE={'V19_SHA256_manifest.json','V20_SHA256_manifest.json'}

def files():
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and not (set(p.relative_to(ROOT).parts)&SKIP_DIRS) and p.suffix not in SKIP_SUFFIX and p.name not in EXCLUDE:
            yield p

def main():
    manifest={}
    for p in files():
        manifest[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    m=ROOT/'V20_SHA256_manifest.json'
    m.write_text(json.dumps({'version':'2.0.0','source':'V1.9+V2.0 incremental','files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as archive:
        for p in files():archive.write(p,arcname=PREFIX+'/'+p.relative_to(ROOT).as_posix())
        archive.write(m,arcname=PREFIX+'/'+m.name)
    with zipfile.ZipFile(OUT) as archive:
        assert archive.testzip() is None
        for rel,expected in manifest.items():
            digest=hashlib.sha256(archive.read(PREFIX+'/'+rel)).hexdigest()
            assert digest==expected,(rel,digest,expected)
    print(json.dumps({'zip':str(OUT),'files':len(manifest)+1,'size_bytes':OUT.stat().st_size},ensure_ascii=False))
if __name__=='__main__':main()
