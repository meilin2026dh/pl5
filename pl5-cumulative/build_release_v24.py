"""Deterministic-ish source archive of PL5 V2.4. Does not overwrite prior zips."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parent
DEST=ROOT.parent.parent/'PL5_V2.4_九空间特征与时序协同科研_完整部署包.zip'
EXCLUDE={'.pytest_cache','__pycache__','.venv','.git','node_modules'}

def files():
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or any(x in EXCLUDE for x in p.relative_to(ROOT).parts):continue
        if p.suffix in {'.pyc','.pyo','.tmp','.bak'}:continue
        if p.name in {'V24_SHA256_manifest.json'}:continue
        yield p

if __name__=='__main__':
    records=[]
    for p in files():
        path=p.relative_to(ROOT).as_posix()
        raw=p.read_bytes()
        records.append({'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
    manifest={'version':'2.4.0','source':'pl5_v24_source','files':records,
              'method':'SHA256 of uncompressed file bytes; excludes this manifest'}
    manifest_raw=json.dumps(manifest,indent=2,ensure_ascii=False).encode('utf-8')
    (ROOT/'V24_SHA256_manifest.json').write_bytes(manifest_raw)
    with zipfile.ZipFile(DEST,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in files():z.write(p,arcname=p.relative_to(ROOT).as_posix())
        z.writestr('V24_SHA256_manifest.json',manifest_raw)
    print(json.dumps({'archive':str(DEST),'files':len(records),'compressed_bytes':DEST.stat().st_size},ensure_ascii=False))
