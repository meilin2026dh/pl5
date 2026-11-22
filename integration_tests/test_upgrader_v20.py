from pathlib import Path
import pytest
from test_upgrader_v151 import _fixture
from upgrade_github_overlay_v20 import upgrade

def test_additive_upgrade_and_idempotence(tmp_path):
    root=_fixture(tmp_path)
    assert upgrade(root)['state']=='installed'
    assert upgrade(root)['state']=='already_applied'
    w=(root/'src/pages/Workbench.tsx').read_text()
    s=(root/'server/index.mjs').read_text()
    assert w.count('<PaperFactoryV20 />')==1
    assert s.count('req.url === "/api/esse/paper-factory"')==1
    assert 'paperFactory' in (root/'server/esseProxy.mjs').read_text()

def test_local_mutation_blocks_update(tmp_path):
    root=_fixture(tmp_path);upgrade(root)
    x=root/'src/components/PaperFactoryV20.tsx';x.write_text('custom')
    with pytest.raises(RuntimeError):upgrade(root)
    assert x.read_text()=='custom'
