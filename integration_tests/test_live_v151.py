"""Actual Node -> Python HTTP test, not mocked HTTP. Requires node>=18."""
from http.server import ThreadingHTTPServer
from pathlib import Path
import os
import shutil
import subprocess
import threading
import pytest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"research_backend"))
from integration_server import BridgeHandler

@pytest.mark.skipif(not shutil.which('node'),reason='Node.js not installed')
def test_real_cross_process_status(tmp_path):
    server=ThreadingHTTPServer(('127.0.0.1',0),BridgeHandler)
    t=threading.Thread(target=server.serve_forever,daemon=True)
    t.start()
    try:
        env={**os.environ,'PL5_BRIDGE_PORT':str(server.server_address[1]),
             'PL5_REGISTRY_PATH':str(tmp_path/'missing.sqlite')}
        p=subprocess.run(['node',str(Path(__file__).with_name('smoke_node_proxy_v151.mjs'))],
                         env=env,capture_output=True,text=True,timeout=15)
        assert p.returncode==0,p.stderr+'\n'+p.stdout
        assert 'smoke passed' in p.stdout
        assert not (tmp_path/'missing.sqlite').exists()
    finally:
        server.shutdown();server.server_close();t.join(3)
