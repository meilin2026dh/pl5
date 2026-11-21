from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).parent
files=[]
for file in root.rglob('*'):
    if not file.is_file():continue
    rel=file.relative_to(root)
    if file.name in {'build_release.py'}:continue
    if any(s in rel.parts for s in ('__pycache__','.pytest_cache','.venv','runtime')):continue
    if file.suffix in ('.pyc','.zip'):continue
    files.append((file,rel))
manifest={str(rel).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest() for path,rel in files}
manifest_path=root/'V12_SHA256_manifest.json'
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
files.append((manifest_path,manifest_path.relative_to(root)))
out=Path('/mnt/data/PL5_V1.2_五序统一融合与ESSE跨语言桥接_完整部署包.zip')
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
    for path,rel in sorted(files,key=lambda x:str(x[1])):
        z.write(path,arcname=str(rel).replace('\\','/'))
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    for rel,digest in manifest.items():
        assert hashlib.sha256(z.read(rel)).hexdigest()==digest,(rel,digest)
print(out,'files',len(files),'bytes',out.stat().st_size)
