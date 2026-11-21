"""Verify V3.7.20 release file hashes after extraction. Python 3.12+ stdlib only."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def verify(root: Path) -> dict:
    manifest_path=root/'PL5_V3720_MANIFEST.json'
    manifest=json.loads(manifest_path.read_text('utf-8'))
    if manifest.get('schema')!='pl5-v3720-manifest-1':
        raise ValueError('unsupported release manifest')
    errors=[]
    for item in manifest['files']:
        path=root/item['path']
        if not path.is_file():
            errors.append('MISSING '+item['path'])
            continue
        data=path.read_bytes()
        if len(data)!=item['size'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
            errors.append('CORRUPT '+item['path'])
    return {'release':'V3.7.20','manifest_count':len(manifest['files']),
            'checked':len(manifest['files']), 'errors':errors,
            'passed':len(errors)==0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    a=p.parse_args()
    out=verify(a.root)
    print(json.dumps(out,ensure_ascii=False,indent=2))
    if not out['passed']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
