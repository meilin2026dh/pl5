from pathlib import Path
from hashlib import sha256
import json,zipfile, tempfile
ROOT=Path(__file__).resolve().parent
OUTPUT=Path('/mnt/data/PL5_V1.7_长期自主科研调度与官方开奖归档_完整部署包.zip')
EX_DIR={'.pytest_cache','__pycache__','.cache','.venv','node_modules','dist','runtime','research_reports'}
EX_FILES={'build_release_v17.py'}
entries=[]
for p in ROOT.rglob('*'):
    if not p.is_file():continue
    rel=p.relative_to(ROOT)
    if any(part in EX_DIR for part in rel.parts):continue
    if p.name in EX_FILES or p.suffix.lower() in {'.pyc','.db','.sqlite','.log','.zip'}:continue
    if rel.as_posix() in {'V16_SHA256_manifest.json','V17_SHA256_manifest.json'}:continue
    entries.append((rel.as_posix(),p))
entries.sort(key=lambda item:item[0])
checks={rel:sha256(path.read_bytes()).hexdigest() for rel,path in entries}
manifest={'version':'1.7.0','source_based_on':'PL5 V1.6 plus GitHub safe overlay',
          'complete_github_frontend_included':False,'files':checks}
with zipfile.ZipFile(OUTPUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
    for rel,path in entries:z.write(path,arcname=rel)
    z.writestr('V17_SHA256_manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
with zipfile.ZipFile(OUTPUT) as z:
    assert z.testzip() is None
    obj=json.loads(z.read('V17_SHA256_manifest.json'))
    assert len(obj['files'])==len(entries)
    for path,expected in obj['files'].items():
        assert sha256(z.read(path)).hexdigest()==expected,path
print(json.dumps({'zip':str(OUTPUT),'files':len(entries),'bytes':OUTPUT.stat().st_size,
                  'manifest_entries':len(checks),'all_sha256_verified':True},ensure_ascii=False))
