import pytest
from test_upgrader_v151 import _fixture
from upgrade_github_overlay_v17 import upgrade


def test_upgrade_v17_adds_read_only_panel_and_is_idempotent(tmp_path):
    repo=_fixture(tmp_path)
    out=upgrade(repo)
    assert out['state']=='installed'
    wb=(repo/'src/pages/Workbench.tsx').read_text('utf8')
    assert wb.count('<ResearchOpsV17 />')==1
    assert (repo/'src/components/ResearchOpsV17.tsx').is_file()
    assert upgrade(repo)['state']=='already_applied'


def test_upgrade_v17_detects_modified_panel(tmp_path):
    repo=_fixture(tmp_path)
    upgrade(repo)
    file=repo/'src/components/ResearchOpsV17.tsx'
    file.write_text('personal modification',encoding='utf8')
    with pytest.raises(RuntimeError):upgrade(repo)
    assert file.read_text('utf8')=='personal modification'
