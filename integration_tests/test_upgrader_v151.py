from pathlib import Path
import pytest
from upgrade_github_overlay_v151 import upgrade


def _fixture(tmp_path):
    root=tmp_path/'frontend'
    (root/'src/pages').mkdir(parents=True)
    (root/'server').mkdir()
    (root/'src/pages/Workbench.tsx').write_text('''import DiscoveryLab from "../components/DiscoveryLab";
export default function Workbench() { return (
  <>
          <ConditionLab input={input} onChange={setInput} />
  </>); }
''')
    (root/'server/index.mjs').write_text('''import { createServer } from "node:http";
const server = createServer(async (req, res) => {
  res.end('ok');
});
''')
    return root


def test_fresh_upgrade_and_idempotence(tmp_path):
    root=_fixture(tmp_path)
    a=upgrade(root)
    assert a['state']=='installed'
    assert 'PL5-V1.5.1-EVOLUTION-STATUS' in (root/'src/pages/Workbench.tsx').read_text()
    assert '<EvolutionStatus />' in (root/'src/pages/Workbench.tsx').read_text()
    assert '"/api/esse/status"' in (root/'server/index.mjs').read_text()
    assert (root/'src/components/EvolutionStatus.tsx').is_file()
    assert upgrade(root)['state']=='already_applied'


def test_custom_proxy_rejected(tmp_path):
    root=_fixture(tmp_path)
    upgrade(root)
    proxy=root/'server/esseProxy.mjs'
    proxy.write_text(proxy.read_text()+'\n// user customization\n')
    with pytest.raises(RuntimeError):upgrade(root)


def test_missing_anchor_fails(tmp_path):
    root=_fixture(tmp_path)
    (root/'src/pages/Workbench.tsx').write_text('broken')
    with pytest.raises(RuntimeError):upgrade(root)
