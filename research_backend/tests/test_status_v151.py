import io
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
from integration_server import BridgeHandler
from status_v151 import status
from pailie5.algorithm_registry_v14 import Registry
from pailie5.evolution_v15 import EvolutionLab
from snapshot_v15 import OFFICIAL_URL

class HandlerHarness(BridgeHandler):
    def __init__(self,path):
        self.path=path;self.wfile=io.BytesIO();self.headers={};self.status_code=None
    def send_response(self,status):self.status_code=status
    def send_header(self,*args):pass
    def end_headers(self):pass
    def log_message(self,*args):pass


def test_missing_not_created(tmp_path):
    db=tmp_path/'missing.sqlite'; cache=tmp_path/'missing.json'
    a=status(registry_path=db,official_cache_path=cache)
    assert a['registry']['state']=='file_missing'
    assert a['official_cache']['state']=='file_missing'
    assert not db.exists() and not cache.exists()
    assert not a['safe_modes']['auto_approval']


def test_real_readonly_registry_counts_no_mutations(tmp_path):
    db=tmp_path/'study.sqlite'
    r=Registry(db)
    try:
        EvolutionLab(r)
        banned=np.zeros(100000,dtype=bool)
        banned[100:1000]=True
        r.register(title='test_rule',family='time',creator='scientist',source_ref='synthetic',
            cutoff_issue='26290',cutoff_date='2026-10-31',data_sha256='a'*64,excluded=banned)
        before=r.db.execute('SELECT COUNT(*) FROM events').fetchone()[0]
    finally:r.close()
    a=status(registry_path=db)
    assert a['registry']['state']=='ready'
    assert a['registry']['counts']['candidate']==1
    assert a['registry']['ledger_verified'] is True
    r=Registry(db)
    try:
        assert before==r.db.execute('SELECT COUNT(*) FROM events').fetchone()[0]
    finally:r.close()


def test_cache_fresh_and_stale(tmp_path):
    p=tmp_path/'history.json'
    p.write_text(json.dumps({'sourceUrl':OFFICIAL_URL,
        'updatedAt':datetime.now(timezone.utc).isoformat(),
        'draws':[{'issue':'26290','date':'2026-10-31','number':'00127'}]}))
    a=status(official_cache_path=p)
    assert a['official_cache']['state']=='fresh_structurally_valid'
    assert a['official_cache']['latest_issue']=='26290'
    assert a['official_cache']['origin_cryptographically_verified'] is False
    raw=json.loads(p.read_text());raw['stale']=True;p.write_text(json.dumps(raw))
    assert status(official_cache_path=p)['official_cache']['state']=='invalid_or_stale'


def test_http_new_status_endpoint(tmp_path):
    h=HandlerHarness('/api/esse/status')
    with patch.dict('os.environ',{'PL5_REGISTRY_PATH':str(tmp_path/'missing.db'),
                                  'PL5_OFFICIAL_CACHE':str(tmp_path/'missing.json')}):
        h.do_GET()
    assert h.status_code==200
    body=json.loads(h.wfile.getvalue())
    assert body['schema']=='pl5-live-status-v151'
    assert body['registry']['state']=='file_missing'
    assert not (tmp_path/'missing.db').exists()
