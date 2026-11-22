import pytest
from test_upgrader_v151 import _fixture
from upgrade_github_overlay_v16 import upgrade


def test_v16_upgrade_and_idempotence(tmp_path):
    repo=_fixture(tmp_path)
    out=upgrade(repo)
    assert out['state']=='installed'
    assert '<ValueCenter />' in (repo/'src/pages/Workbench.tsx').read_text()
    assert (repo/'src/components/ValueCenter.tsx').is_file()
    assert upgrade(repo)['state']=='already_applied'


def test_v16_conflict_preserves_user_component(tmp_path):
    repo=_fixture(tmp_path)
    upgrade(repo)
    c=repo/'src/components/ValueCenter.tsx'
    c.write_text('my custom rules',encoding='utf8')
    with pytest.raises(RuntimeError):upgrade(repo)
    assert c.read_text()=='my custom rules'
