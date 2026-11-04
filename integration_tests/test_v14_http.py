"""V1.4 real loopback service integration with approved research mask."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

import numpy as np

ROOT=Path(__file__).resolve().parent.parent
BACKEND=ROOT/'research_backend'
sys.path.insert(0,str(BACKEND))
from pailie5.algorithm_registry_v14 import Registry
from pailie5.integration_bridge import SCHEMA, encode_mask


def test_registered_rule_via_http(tmp_path):
    dbpath=tmp_path/'registry.sqlite'
    db=Registry(dbpath)
    ban=np.zeros(100000,dtype=bool);ban[:5000]=True
    key=db.register(title='demo',family='math',creator='algorithm-agent',
       source_ref='offline-test',cutoff_issue='26290',cutoff_date='2026-10-20',
       data_sha256=hashlib.sha256(b'train').hexdigest(),excluded=ban)['id']
    draws=[{'issue':str(26300+i),'date':f'2026-11-{i+1:02d}',
            'number':f'{i*997:05d}'} for i in range(12)]
    audit=db.evaluate_holdout(key,draws,snapshot_sha256=hashlib.sha256(b'future').hexdigest())
    db.approve_experimental(key,experiment_id=audit['experiment_id'],reviewer='independent-reviewer',
                           consent='APPROVE_EXPERIMENTAL_NOT_PREDICTIVE')
    db.close()
    full=encode_mask(np.ones(100000,dtype=bool))
    req={'schema':SCHEMA,'combination':'strict','k':30,'seed':2026,'rules':[],
         'base':full,'strict_kept':full,'expected_strict_keep':100000,
         'protocol_upgrade':'v13_verified','registered_rule_ids':[key],
         'meta':{'reference_issue':'26290','history_source':'offline-fixture'}}
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env={**os.environ,'PL5_REGISTRY_PATH':str(dbpath),'PL5_BRIDGE_PORT':str(port)}
    proc=subprocess.Popen([sys.executable,'integration_server.py'],cwd=BACKEND,env=env,
                          stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        for _ in range(80):
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{port}/api/esse/health',timeout=1).read()
                break
            except Exception:time.sleep(0.1)
        else:raise RuntimeError('service did not start')
        payload=json.dumps(req).encode()
        request=urllib.request.Request(f'http://127.0.0.1:{port}/api/esse/sculpt',data=payload,
                                       headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=15) as response:
            res=json.loads(response.read())
        assert res['registered_rule_count']==1
        assert res['typescript_strict_keep_count']==100000
        assert res['strict_keep_count']==95000
        assert res['selected_count']==30
        assert all(int(n)>=5000 for n in res['top_numbers'])
    finally:
        proc.terminate()
        try: proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.communicate()
