"""Rebuild a V3723 manifest/full/patch pair from an intact extracted workspace.

Only for trusted local code; verify previous ZIP path separately. Does not edit
existing historical sources except intended release notes/version metadata.
"""
from __future__ import annotations
import argparse,hashlib,json,zipfile
from pathlib import Path

IGNORE={'__pycache__','.pytest_cache'}


def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def files(root):
    return {p.relative_to(root).as_posix():p for p in root.rglob('*') if p.is_file()
            and not any(part in IGNORE for part in p.parts) and p.suffix!='.pyc'}


def write(path,document):
    path.write_text(json.dumps(document,indent=2,sort_keys=True,ensure_ascii=False)+'\n','utf-8')


def pack(path,workspace,names):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in sorted(names):
            if name.startswith('/') or '..' in Path(name).parts:raise ValueError('illegal archive path')
            info=zipfile.ZipInfo(name,date_time=(2026,11,5,10,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            z.writestr(info,(workspace/name).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)


def build(root:Path,previous_zip:Path,out:Path):
    if not previous_zip.is_file():raise FileNotFoundError(previous_zip)
    for name in ('PL5_V3723_MANIFEST.json','PL5_V3723_Package_Audit.json'):
        if (root/name).exists():(root/name).unlink()
    with zipfile.ZipFile(previous_zip) as z:
        old={i.filename:sha(z.read(i)) for i in z.infolist() if not i.is_dir()}
    current=files(root)
    paths=set(current)
    if not set(old)<=paths:raise ValueError('historic files missing from release')
    old_changed=sorted(name for name,digest in old.items() if sha(current[name].read_bytes())!=digest)
    authorized={'README.md','research_backend/pailie5/__init__.py','research_backend/pyproject.toml'}
    if set(old_changed)!=authorized:raise ValueError(f'unexpected historic changes: {old_changed}')
    added=sorted(paths-set(old))
    audit={'schema':'pl5-v3723-preservation-audit-1',
           'base_archive_file':previous_zip.name,'base_archive_sha256':sha(previous_zip.read_bytes()),
           'base_file_count':len(old),'inherited_paths':len(set(old)&paths),
           'inherited_unchanged':len(old)-len(old_changed),
           'inherited_modified':old_changed,'removed':[],
           'new_files_excluding_manifest_and_audit':len(added),
           'source_26295_seal_files_preserved':all(name not in old_changed for name in old if '26295' in name),
           'all_base_paths_preserved':True,'history_claim':'cumulative relative to V3.7.22, not verified independent snapshots for every version'}
    auditpath=root/'PL5_V3723_Package_Audit.json';write(auditpath,audit)
    current=files(root)
    entries=[]
    for path,p in sorted(current.items()):
        b=p.read_bytes();entries.append({'path':path,'size':len(b),'sha256':sha(b)})
    manifest={'schema':'pl5-v3723-full-manifest-1','version':'3.7.23',
              'base_archive_sha256':audit['base_archive_sha256'],
              'file_count_excluding_manifest':len(entries),
              'base_file_count':len(old),'new_files_including_audit':len(current)-len(old),
              'preexisting_unchanged':audit['inherited_unchanged'],
              'preexisting_modified':old_changed,
              'no_external_blind_test':True,'real_lottery_advantage':'NOT_ESTABLISHED',
              'files':entries}
    write(root/'PL5_V3723_MANIFEST.json',manifest)
    current=files(root)
    full=out/'PL5_V3723_Research_Full.zip';pack(full,root,current)
    patchnames=set(added)|set(old_changed)|{'PL5_V3723_Package_Audit.json','PL5_V3723_MANIFEST.json'}
    patch=out/'PL5_V3723_Research_Patch.zip';pack(patch,root,patchnames)
    return {'full':str(full),'patch':str(patch),
            'previous_count':len(old),'current_count':len(current),
            'new_with_audit_manifest':len(current)-len(old),'changed':old_changed,
            'patch_count':len(patchnames),'audit':audit}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(build(args.root,args.base,args.out),ensure_ascii=False,indent=2))
