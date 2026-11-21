from __future__ import annotations
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'PL5_V2.1_多智能体协同科研与科学证伪_完整部署包.zip'
SKIP={'.pytest_cache','__pycache__','.git','node_modules','.venv','.mypy_cache','.ruff_cache'}
NO={'.pyc','.pyo','.db','.sqlite','.log','.tmp'}
SKIP_FILES={'V19_SHA256_manifest.json','V20_SHA256_manifest.json','V21_SHA256_manifest.json'}
PREFIX='pl5_v21_collab'

def filelist():
    for f in sorted(ROOT.rglob('*')):
        if f.is_file() and not set(f.relative_to(ROOT).parts)&SKIP and f.suffix not in NO and f.name not in SKIP_FILES:
            yield f

def main():
    manifest={f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in filelist()}
    m=ROOT/'V21_SHA256_manifest.json'
    m.write_text(json.dumps({'version':'2.1.0','base':'V2.0','files':manifest},indent=2,ensure_ascii=False),encoding='utf8')
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as archive:
        for f in filelist():archive.write(f,arcname=PREFIX+'/'+f.relative_to(ROOT).as_posix())
        archive.write(m,arcname=PREFIX+'/'+m.name)
    with zipfile.ZipFile(OUT) as archive:
        assert archive.testzip() is None
        for rel,d in manifest.items():assert hashlib.sha256(archive.read(PREFIX+'/'+rel)).hexdigest()==d,rel
    print(json.dumps({'zip':str(OUT),'files':len(manifest)+1,'bytes':OUT.stat().st_size},ensure_ascii=False))

if __name__=='__main__':main()
