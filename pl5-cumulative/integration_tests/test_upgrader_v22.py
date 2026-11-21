from pathlib import Path
import pytest
from test_upgrader_v151 import _fixture
from upgrade_github_overlay_v22 import upgrade


def test_v22_installer_is_idempotent(tmp_path):
    root=_fixture(tmp_path)
    assert upgrade(root)['state']=='installed'
    assert upgrade(root)['state']=='already_applied'
    wb=(root/'src/pages/Workbench.tsx').read_text()
    server=(root/'server/index.mjs').read_text()
    assert wb.count('<ResearchCollabV22 />')==1
    assert server.count('req.url === "/api/esse/research-v22"')==1
    proxy=(root/'server/esseProxy.mjs').read_text()
    assert 'const researchV22=' in proxy
    assert '|| researchV22?"GET"' in proxy
    assert '|| researchV22?undefined' in proxy


def test_modified_v22_component_is_preserved(tmp_path):
    root=_fixture(tmp_path);upgrade(root)
    component=root/'src/components/ResearchCollabV22.tsx'
    component.write_text('// local edit',encoding='utf8')
    with pytest.raises(RuntimeError):upgrade(root)
    assert component.read_text('utf8')=='// local edit'
