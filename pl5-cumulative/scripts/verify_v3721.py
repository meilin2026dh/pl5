"""Verify V3.7.21 build file checksums after extraction (not authenticity)."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def verify(root:Path):
    manifest=root/'PL5_V3721_MANIFEST.json'
    info=json.loads(manifest.read_text('utf-8'))
    assert info['schema']=='pl5-v3721-manifest-1'
    entries=info['files']
    assert len(entries)==info['file_count_excluding_manifest']
    paths=[]
    for record in entries:
        name=record['path']
        path=PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts and '\\' not in name
        data=(root/name).read_bytes()
        assert len(data)==record['size'],f'{name}: size mismatch'
        assert hashlib.sha256(data).hexdigest()==record['sha256'],f'{name}: SHA256 mismatch'
        paths.append(name)
    assert len(set(paths))==len(paths)
    print(json.dumps({'status':'PASS','verified_regular_files':len(paths)+1,
                      'source_preserved_count':info['unchanged_parent_files'],
                      'release':info['release']},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'))
    verify(p.parse_args().root)
