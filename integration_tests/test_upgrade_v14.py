from pathlib import Path
import hashlib
import importlib.util
import sys
import shutil
import pytest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'integration_tests'))
from upgrade_github_overlay_v14 import upgrade


def frontend(tmp_path,patched=True):
    f=tmp_path/'frontend'
    for part in ('src/pages','src/components','src/workers','server','tests'):
        (f/part).mkdir(parents=True,exist_ok=True)
    wb='import DiscoveryLab from "../components/DiscoveryLab";\n'
    wb+='export default function Workbench(){return(<>\n          <ConditionLab input={input} onChange={setInput} />\n</>)}'
    server='import { createServer } from "node:http";\nconst server = createServer(async (req, res) => {\n});\n'
    if patched:
        wb='// PL5-V1.2-ESSE-INTEGRATION\nimport EsseBridge from "../components/EsseBridge";\n'+wb
        wb=wb.replace('          <ConditionLab','          <EsseBridge input={input} onChange={setInput} />\n          <ConditionLab')
        server='// PL5-V1.2-ESSE-INTEGRATION\nimport { handleEsseProxy } from "./esseProxy.mjs";\n'+server
        server=server.replace('const server = createServer(async (req, res) => {', 'const server = createServer(async (req, res) => {\n  if (req.url === "/api/esse/health" || req.url === "/api/esse/sculpt") {\n    await handleEsseProxy(req, res);\n    return;\n  }')
        for rel in ('server/esseProxy.mjs','tests/esse-integration.test.ts'):
            shutil.copy2(ROOT/'github_overlay'/rel,f/rel)
        for rel in ('src/components/EsseBridge.tsx','src/workers/esse.worker.ts'):
            shutil.copy2(ROOT/'integration_tests/fixtures/v13'/rel,f/rel)
    (f/'src/pages/Workbench.tsx').write_text(wb)
    (f/'server/index.mjs').write_text(server)
    return f


def test_existing_v13_overlay_upgrade(tmp_path):
    f=frontend(tmp_path)
    result=upgrade(f)
    assert result['mode']=='upgrade-v12-or-v13'
    assert len(result['changed'])==2
    assert (f/'src/components/EsseBridge.tsx.v13-before-v14.bak').exists()
    assert upgrade(f)['changed']==[]


def test_unknown_user_customization_refused(tmp_path):
    f=frontend(tmp_path)
    p=f/'src/components/EsseBridge.tsx'
    p.write_text(p.read_text()+'\n// user-custom-code')
    with pytest.raises(RuntimeError,match='用户自定义'):
        upgrade(f)
    assert not list(f.rglob('*.v13-before-v14.bak'))


def test_clean_checkout_bootstrapped(tmp_path):
    f=frontend(tmp_path,patched=False)
    result=upgrade(f)
    assert result['mode']=='new'
    assert 'EsseBridge' in (f/'src/pages/Workbench.tsx').read_text()
    assert (f/'src/components/EsseBridge.tsx').exists()


def test_inconsistent_frontend_server_rejected(tmp_path):
    f=frontend(tmp_path)
    s=f/'server/index.mjs'
    s.write_text(s.read_text().replace('// PL5-V1.2-ESSE-INTEGRATION','// edited'))
    with pytest.raises(RuntimeError,match='标记不一致'):
        upgrade(f)
