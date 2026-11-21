import json
from unittest.mock import patch
from test_bridge_server_v12 import HandlerHarness
from pailie5.capability_network import CapabilityRegistry, bootstrap, grow


def test_read_only_capability_route(tmp_path):
    path=tmp_path/'capabilities.sqlite'
    with patch.dict('os.environ',{'PL5_AAN_DB':str(path)}):
        h=HandlerHarness(method='GET',path='/api/esse/capabilities');h.do_GET()
        assert json.loads(h.wfile.getvalue())['status']=='not_initialized'
        db=CapabilityRegistry(path)
        bootstrap(db);grow(db,limit=2);db.close()
        h=HandlerHarness(method='GET',path='/api/esse/capabilities');h.do_GET()
        body=json.loads(h.wfile.getvalue())
        assert h.status==200
        assert body['count']==12
        assert body['predictive_advantage']=='NOT_ESTABLISHED'
        assert len(body['edges'])==6
