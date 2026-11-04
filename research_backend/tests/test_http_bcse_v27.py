"""Real localhost HTTP boundary; no external service dependency."""
import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import numpy as np
from integration_server import BridgeHandler


def test_v27_http_contract():
    server=ThreadingHTTPServer(('127.0.0.1',0),BridgeHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    def post(body):
        req=Request(base+'/api/esse/bcse-v27/research',data=json.dumps(body).encode(),
                    headers={'Content-Type':'application/json'},method='POST')
        try:
            with urlopen(req,timeout=40) as resp:return resp.status,json.load(resp)
        except HTTPError as err:return err.code,json.loads(err.read())
    try:
        with urlopen(base+'/api/esse/bcse-v27/capabilities') as res: cards=json.load(res)
        assert len(cards['constraints'])==6
        assert post({})[1]['status']=='research_hypotheses_only'
        assert post({'history':['12abc']*160})[0]==422
        assert post({'history':['12345']*160,'null_trials':2})[0]==422
        data=[f'{i:05d}' for i in np.random.default_rng(12).integers(100000,size=155)]
        status,body=post({'history':data,'budget':9,'validation_periods':20,'test_periods':20})
        assert status==200 and len(body['experimental_top_k'])==9
        assert body['predictive_advantage']=='UNVERIFIED'
    finally:
        server.shutdown();server.server_close()
