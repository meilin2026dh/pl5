from pathlib import Path
import pytest
from test_upgrader_v151 import _fixture
from upgrade_github_overlay_v19 import upgrade

def test_additive_upgrade_and_idempotence(tmp_path):
    root=_fixture(tmp_path)
    assert upgrade(root)['state']=='installed'
    assert upgrade(root)['state']=='already_applied'
    assert '<AbilityLabV19 />' in (root/'src/pages/Workbench.tsx').read_text()
    assert 'req.url === "/api/esse/ability-lab"' in (root/'server/index.mjs').read_text()
    assert 'abilityLab' in (root/'server/esseProxy.mjs').read_text()

def test_modified_existing_component_blocks_upgrade(tmp_path):
    root=_fixture(tmp_path);upgrade(root)
    x=root/'src/components/AbilityLabV19.tsx';x.write_text('local edit')
    with pytest.raises(RuntimeError):upgrade(root)
    assert x.read_text()=='local edit'
