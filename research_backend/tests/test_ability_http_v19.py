import json
from unittest.mock import patch
from test_bridge_server_v12 import HandlerHarness
from pailie5.ability_lab_v19 import AbilityLab,Goal

def test_ability_lab_read_only_status(tmp_path):
    db=tmp_path/'lab.sqlite'
    with patch.dict('os.environ',{'PL5_AAN_DB':str(db)}):
        h=HandlerHarness(method='GET',path='/api/esse/ability-lab');h.do_GET()
        assert json.loads(h.wfile.getvalue())['status']=='not_initialized'
        with AbilityLab(db) as lab:lab.run(Goal('cross_position',1))
        h=HandlerHarness(method='GET',path='/api/esse/ability-lab');h.do_GET()
        x=json.loads(h.wfile.getvalue())
        assert h.status==200 and x['total']==1 and x['proposals'][0]['report']['full_space_parity']
