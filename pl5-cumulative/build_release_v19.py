"""Create reproducible release archive with content SHA256 verification."""
from __future__ import annotations
import hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT.parent/'PL5_V1.9_算法能力缺口发现与自主创新_完整部署包.zip'
SKIP={'__pycache__','.pytest_cache','.ruff_cache','.mypy_cache','.venv','node_modules','.git'}
SKIP_SUFFIX={'.pyc','.pyo','.sqlite','.db','.log','.tmp'}

def iter_files():
    for p in ROOT.rglob('*'):
        if p.is_file() and not set(p.relative_to(ROOT).parts).intersection(SKIP) and p.suffix not in SKIP_SUFFIX and p.name!='V19_SHA256_manifest.json':
            yield p

def main():
    manifest={}
    for p in sorted(iter_files()):
        rel=p.relative_to(ROOT).as_posix()
        manifest[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    (ROOT/'V19_SHA256_manifest.json').write_text(json.dumps({'version':'1.9','files':manifest},indent=2,ensure_ascii=False),encoding='utf8')
    if OUTPUT.exists():OUTPUT.unlink()
    with zipfile.ZipFile(OUTPUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(iter_files()):z.write(p,arcname=ROOT.name+'/'+p.relative_to(ROOT).as_posix())
        z.write(ROOT/'V19_SHA256_manifest.json',arcname=ROOT.name+'/V19_SHA256_manifest.json')
    with zipfile.ZipFile(OUTPUT) as z:
        assert z.testzip() is None
        for rel,h in manifest.items():
            assert hashlib.sha256(z.read(ROOT.name+'/'+rel)).hexdigest()==h,rel
    print('release',OUTPUT,'files',len(manifest)+1,'size',OUTPUT.stat().st_size)
if __name__=='__main__':main()
