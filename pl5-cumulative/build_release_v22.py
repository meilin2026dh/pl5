"""Deterministic release packaging and SHA256 full-file verification."""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json
import zipfile

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'PL5_V2.2_自主算法工程与异构反例验证_完整部署包.zip'
PREFIX='pl5_v22_collab'
SKIP_DIR={'.pytest_cache','__pycache__','.git','node_modules','.venv','.mypy_cache','.ruff_cache'}
SKIP_EXT={'.pyc','.pyo','.db','.sqlite','.log','.tmp'}
SKIP_FILES={'V19_SHA256_manifest.json','V20_SHA256_manifest.json','V21_SHA256_manifest.json','V22_SHA256_manifest.json'}

def candidates():
    for f in sorted(ROOT.rglob('*')):
        if (f.is_file() and not set(f.relative_to(ROOT).parts)&SKIP_DIR
            and f.suffix not in SKIP_EXT and f.name not in SKIP_FILES):
            yield f

def main():
    files=list(candidates())
    manifest={f.relative_to(ROOT).as_posix():sha256(f.read_bytes()).hexdigest() for f in files}
    path=ROOT/'V22_SHA256_manifest.json'
    path.write_text(json.dumps({'version':'2.2.0','base':'V2.1','files':manifest},indent=2,ensure_ascii=False),encoding='utf8')
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as archive:
        for f in files:archive.write(f,arcname=PREFIX+'/'+f.relative_to(ROOT).as_posix())
        archive.write(path,arcname=PREFIX+'/'+path.name)
    with zipfile.ZipFile(OUT) as archive:
        assert archive.testzip() is None
        for rel,checksum in manifest.items():
            assert sha256(archive.read(PREFIX+'/'+rel)).hexdigest()==checksum,rel
    print(json.dumps({'zip':str(OUT),'files':len(files)+1,'size_bytes':OUT.stat().st_size},ensure_ascii=False))

if __name__=='__main__': main()
