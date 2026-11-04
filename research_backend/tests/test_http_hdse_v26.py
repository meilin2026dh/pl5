import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import numpy as np
from integration_server import BridgeHandler


def test_http_capabilities_and_boundaries():
    srv=ThreadingHTTPServer(('127.0.0.1',0),BridgeHandler)
    t=threading.Thread(target=srv.serve_forever,daemon=True);t.start()
    url=f'http://127.0.0.1:{srv.server_port}'
    def post(body):
        req=Request(url+'/api/esse/hdse-v26/research',
                    data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
        try:
            with urlopen(req,timeout=30) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.loads(e.read())
    try:
        with urlopen(url+'/api/esse/hdse-v26/capabilities') as r:
            x=json.load(r)
        assert len(x['capabilities'])==7
        code,proposed=post({'maximum':4})
        assert code==200 and len(proposed['proposals'])==4
        code,failed=post({'history':['1234']*160})
        assert code==422 and failed['error']=='validation'
        code,failed=post({'null_trials':10})
        assert code==422
        history=[f'{n:05d}' for n in np.random.default_rng(9).integers(100000,size=160)]
        code,experiment=post({'history':history,'maximum':3,'budget':9,'test_periods':30})
        assert code==200 and len(experiment['experimental_top_k'])==9
        assert experiment['status']=='research_only'
    finally:
        srv.shutdown();srv.server_close()
