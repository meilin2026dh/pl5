from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import shutil
from upgrade_github_overlay_v13 import upgrade, V12_SHA256

PACKAGE=Path(__file__).resolve().parents[1]
PREVIOUS=PACKAGE/'integration_tests/v12_baseline'

def base(root:Path):
    (root/'src/pages').mkdir(parents=True)
    (root/'server').mkdir()
    (root/'src/pages/Workbench.tsx').write_text(
        'import DiscoveryLab from "../components/DiscoveryLab";\n'
        'export function Example(){return (<>\n'
        '          <ConditionLab input={input} onChange={setInput} />\n'
        '</>)}', encoding='utf-8')
    (root/'server/index.mjs').write_text(
        'import { createServer } from "node:http";\n'
        'const server = createServer(async (req, res) => {\n'
        'res.end("ok");\n});\n',encoding='utf-8')

def test_clean_and_idempotent():
  with TemporaryDirectory() as p:
    root=Path(p);base(root)
    assert upgrade(root)['mode']=='new'
    assert 'EsseBridge' in (root/'src/pages/Workbench.tsx').read_text()
    assert 'handleEsseProxy' in (root/'server/index.mjs').read_text()
    assert upgrade(root)['mode']=='upgrade-v12'
    assert (root/'src/workers/esse.worker.ts').read_text().count('v13_verified')==1

def test_upgrade_old_and_preserve_custom_edits():
  with TemporaryDirectory() as p:
    root=Path(p);base(root)
    from apply_github_overlay import update
    # Construct original V1.2 patched frontend, using its exact payload and anchors.
    old_payload = PREVIOUS
    for folder in ['src/components','src/workers','tests','server']:
      (root/folder).mkdir(exist_ok=True,parents=True)
      for source in (old_payload/folder).glob('*'):
        if source.is_file():shutil.copy2(source,root/folder/source.name)
    wb=root/'src/pages/Workbench.tsx'
    w=wb.read_text().replace('import DiscoveryLab from "../components/DiscoveryLab";',
        '// PL5-V1.2-ESSE-INTEGRATION\nimport EsseBridge from "../components/EsseBridge";\nimport DiscoveryLab from "../components/DiscoveryLab";')
    w=w.replace('          <ConditionLab input={input} onChange={setInput} />',
        '          <EsseBridge input={input} onChange={setInput} />\n          <ConditionLab input={input} onChange={setInput} />')
    wb.write_text(w)
    server=root/'server/index.mjs'
    s=server.read_text().replace('import { createServer } from "node:http";',
        '// PL5-V1.2-ESSE-INTEGRATION\nimport { handleEsseProxy } from "./esseProxy.mjs";\nimport { createServer } from "node:http";')
    s=s.replace('const server = createServer(async (req, res) => {',
        'const server = createServer(async (req, res) => {\n  if (req.url === "/api/esse/health" || req.url === "/api/esse/sculpt") {\n    await handleEsseProxy(req, res);\n    return;\n  }')
    server.write_text(s)
    upgraded=upgrade(root)
    assert upgraded['mode']=='upgrade-v12'
    assert upgraded['changed']==['server/esseProxy.mjs','src/components/EsseBridge.tsx','src/workers/esse.worker.ts']
    assert (root/'src/workers/esse.worker.ts.v12-before-v13.bak').is_file()
    assert upgrade(root)['changed']==[]
    (root/'src/workers/esse.worker.ts').write_text('// user changed content')
    try:upgrade(root)
    except RuntimeError as e:assert '拒绝覆盖' in str(e)
    else:raise AssertionError('should reject user modifications')

if __name__=='__main__':
 test_clean_and_idempotent();test_upgrade_old_and_preserve_custom_edits();print('Source overlay: new + V1.2 upgrade + safety passed')
