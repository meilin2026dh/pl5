"""Standalone V3.7.23 archive manifest checker. Run from extracted root."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

SKIP={'__pycache__','.pytest_cache'}


def verify(root:Path)->dict:
    manifest=root/'PL5_V3723_MANIFEST.json'
    data=json.loads(manifest.read_text('utf-8'))
    if data.get('schema')!='pl5-v3723-full-manifest-1':
        raise ValueError('unexpected manifest schema')
    recorded={item['path']:item for item in data['files']}
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()
            and not any(part in SKIP for part in p.parts) and p.suffix!='.pyc'
            and p.name!='PL5_V3723_MANIFEST.json'}
    if set(recorded)!=actual:
        raise ValueError(f'path mismatch missing={len(set(recorded)-actual)} extra={len(actual-set(recorded))}')
    for rel,item in recorded.items():
        raw=(root/rel).read_bytes()
        if len(raw)!=item['size'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:
            raise ValueError(f'file checksum mismatch: {rel}')
    if data['file_count_excluding_manifest']!=len(actual):
        raise ValueError('manifest count mismatch')
    return {'status':'PASS','files_checked':len(actual),'with_manifest':len(actual)+1,
            'version':data['version']}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path,nargs='?',default=Path('.'))
    a=p.parse_args();print(json.dumps(verify(a.root),ensure_ascii=False))
