from pathlib import Path
import pytest
from test_upgrader_v151 import _fixture
from upgrade_github_overlay_v18 import upgrade


def test_upgrade_v18_adds_panel_and_route(tmp_path):
    root=_fixture(tmp_path)
    result=upgrade(root)
    assert result['state']=='installed'
    wb=(root/'src/pages/Workbench.tsx').read_text()
    assert wb.count('<CapabilityNetworkV18 />')==1
    assert upgrade(root)['state']=='already_applied'
    assert (root/'server/index.mjs').read_text().count('req.url === "/api/esse/capabilities"')==1
    assert (root/'src/components/CapabilityNetworkV18.tsx').exists()
    assert 'capabilities' in (root/'server/esseProxy.mjs').read_text()


def test_upgrade_v18_conflict_protection(tmp_path):
    root=_fixture(tmp_path)
    upgrade(root)
    c=root/'src/components/CapabilityNetworkV18.tsx'
    c.write_text('local change',encoding='utf8')
    with pytest.raises(RuntimeError):upgrade(root)
    assert c.read_text()=='local change'
