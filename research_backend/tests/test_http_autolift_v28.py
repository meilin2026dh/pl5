import io
import json
from unittest.mock import Mock
from integration_server import BridgeHandler


def fake_handler(path,body=None):
    h=object.__new__(BridgeHandler)
    h.path=path
    content=json.dumps(body or {}).encode('utf-8')
    h.headers={'Content-Type':'application/json','Content-Length':str(len(content))}
    h.rfile=io.BytesIO(content)
    calls=[]
    h._json=lambda status,obj:calls.append((status,obj))
    return h,calls


def test_capabilities_endpoint():
    h,calls=fake_handler('/api/esse/autolift-v28/capabilities')
    h.do_GET()
    assert calls[0][0]==200 and calls[0][1]['status']=='research_only'


def test_refuses_bad_http_arguments():
    h,calls=fake_handler('/api/esse/autolift-v28/research',{'history':'bad','maximum':5})
    h.do_POST()
    assert calls[0][0]==422


def test_http_catalog_no_history():
    h,calls=fake_handler('/api/esse/autolift-v28/research',{'seed':21})
    h.do_POST()
    assert calls[0][0]==200 and calls[0][1]['status']=='research_only'


def test_real_localhost_http_v28():
    from http.server import ThreadingHTTPServer
    from threading import Thread
    from urllib.request import urlopen,Request
    import numpy as np
    server=ThreadingHTTPServer(('127.0.0.1',0),BridgeHandler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        with urlopen(base+'/api/esse/autolift-v28/capabilities',timeout=20) as res:
            assert json.load(res)['status']=='research_only'
        data=[f'{int(x):05d}' for x in np.random.default_rng(19).integers(100000,size=155)]
        req=Request(base+'/api/esse/autolift-v28/research',method='POST',
            data=json.dumps({'history':data,'maximum':3,'budget':9,'validation_periods':20,'test_periods':20}).encode(),
            headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=80) as res:
            result=json.load(res)
            assert result['status']=='research_only'
            assert len(result['experimental_top_k'])==9
    finally:
        server.shutdown();server.server_close()
