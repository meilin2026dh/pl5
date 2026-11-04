"""Emulate Windows Path.write_text newline translation on Linux.

Frozen overlay proxies and components are checked by exact SHA256 bytes;
writing them through the platform text newline converter is unsafe.
"""
from pathlib import Path
import hashlib
import pytest
from test_upgrader_v151 import _fixture
from upgrade_github_overlay_v19 import upgrade as upgrade19
from upgrade_github_overlay_v20 import upgrade as upgrade20
from upgrade_github_overlay_v21 import upgrade as upgrade21
from upgrade_github_overlay_v22 import upgrade as upgrade22

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize('stage,upgrade', [(19, upgrade19), (20, upgrade20),
                                           (21, upgrade21), (22, upgrade22)])
def test_overlay_writes_frozen_bytes_exactly_with_windows_text_translation(
        tmp_path, monkeypatch, stage, upgrade):
    original = Path.write_text

    def windows_write_text(self, data, encoding=None, errors=None, newline=None):
        if self.name.endswith(tuple(f'.v{v}.tmp' for v in range(19, 23))):
            # Windows text-mode translation converts LF into CRLF.
            return self.write_bytes(data.replace('\n', '\r\n').encode(encoding or 'utf8'))
        return original(self, data, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, 'write_text', windows_write_text)
    root = _fixture(tmp_path)
    assert upgrade(root)['state'] == 'installed'
    assert upgrade(root)['state'] == 'already_applied'
    proxy = root/'server/esseProxy.mjs'
    component = {
        19: 'AbilityLabV19.tsx',
        20: 'PaperFactoryV20.tsx',
        21: 'ResearchCouncilV21.tsx',
        22: 'ResearchCollabV22.tsx'
    }[stage]
    for dst, src in [
        (proxy, ROOT/f'github_overlay/server/esseProxy_v{stage}.mjs'),
        (root/'src/components'/component,
         ROOT/'github_overlay/src/components'/component)
    ]:
        assert hashlib.sha256(dst.read_bytes()).digest() == hashlib.sha256(src.read_bytes()).digest()
