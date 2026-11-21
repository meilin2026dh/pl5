import pytest
from test_upgrader_v151 import _fixture
from upgrade_github_overlay_v152 import upgrade

def test_upgrade_and_no_duplicate(tmp_path):
    front=_fixture(tmp_path)
    assert upgrade(front)['state']=='installed'
    assert '<ForwardEvidence />' in (front/'src/pages/Workbench.tsx').read_text()
    assert (front/'src/components/ForwardEvidence.tsx').exists()
    assert upgrade(front)['state']=='already_applied'

def test_conflict_rejected(tmp_path):
    front=_fixture(tmp_path)
    upgrade(front)
    (front/'src/components/ForwardEvidence.tsx').write_text('custom')
    with pytest.raises(RuntimeError):upgrade(front)
