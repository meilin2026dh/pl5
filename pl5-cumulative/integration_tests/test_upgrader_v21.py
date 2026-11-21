from pathlib import Path
import pytest
from test_upgrader_v151 import _fixture
from upgrade_github_overlay_v21 import upgrade

def test_install_and_repeat(tmp_path):
    root=_fixture(tmp_path)
    assert upgrade(root)['state']=='installed'
    assert upgrade(root)['state']=='already_applied'
    wb=(root/'src/pages/Workbench.tsx').read_text()
    srv=(root/'server/index.mjs').read_text()
    assert wb.count('<ResearchCouncilV21 />')==1
    assert srv.count('req.url === "/api/esse/research-council"')==1
    assert 'researchCouncil' in (root/'server/esseProxy.mjs').read_text()

def test_changes_rejected(tmp_path):
    root=_fixture(tmp_path);upgrade(root)
    target=root/'src/components/ResearchCouncilV21.tsx';target.write_text('// user modified')
    with pytest.raises(RuntimeError):upgrade(root)
    assert target.read_text()=='// user modified'


def test_proxy_does_not_read_body_for_council(tmp_path):
    root=_fixture(tmp_path);upgrade(root)
    text=(root/'server/esseProxy.mjs').read_text()
    assert '&& !researchCouncil)' in text
    assert 'const researchCouncil=req.url==="/api/esse/research-council";' in text
