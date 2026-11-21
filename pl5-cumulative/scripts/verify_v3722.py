"""Offline byte integrity verification (NOT signature/authenticity verification)."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def verify(root: Path) -> dict:
    info=json.loads((root/'PL5_V3722_MANIFEST.json').read_text('utf-8'))
    if info['schema']!='pl5-v3722-manifest-1':
        raise ValueError('unexpected version schema')
    entries=info['files']
    if len(entries)!=info['file_count_excluding_manifest']:
        raise ValueError('manifest count mismatch')
    seen=set()
    for item in entries:
        name=item['path']
        pure=PurePosixPath(name)
        if not name or pure.is_absolute() or '..' in pure.parts or '\\' in name or name in seen:
            raise ValueError('invalid or duplicate path')
        seen.add(name)
        path=root/name
        if not path.is_file():
            raise ValueError(f'missing file: {name}')
        raw=path.read_bytes()
        if len(raw)!=item['size'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:
            raise ValueError(f'mismatch: {name}')
    for seal in info['sealed_history_sha256']:
        if seal not in seen:
            raise ValueError(f'missing historical sealed original: {seal}')
        if hashlib.sha256((root/seal).read_bytes()).hexdigest()!=info['sealed_history_sha256'][seal]:
            raise ValueError(f'changed sealed original: {seal}')
    return {'status':'PASS', 'release':info['release'],
            'verified_regular_files':len(seen)+1,
            'prior_files_preserved_identical':info['unchanged_parent_files'],
            'sealed_originals_unchanged':len(info['sealed_history_sha256']),
            'note':'SHA256 integrity only; not independent authenticity'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path('.'))
    print(json.dumps(verify(parser.parse_args().root),ensure_ascii=False))
