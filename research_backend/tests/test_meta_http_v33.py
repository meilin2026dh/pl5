"""V3.3 live HTTP loopback, accept only bounded JSON math tables."""
import json,os,socket,subprocess,sys,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from pailie5.operator_metalearning_v33 import fixtures
ROOT=Path(__file__).resolve().parents[1]

def _call(url,payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=Request(url,data=data,headers={'Content-Type':'application/json'} if data is not None else {})
    with urlopen(req,timeout=30) as response:return json.load(response)

def test_http_scoped_learning_and_validation():
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    proc=subprocess.Popen([sys.executable,'integration_server.py'],cwd=ROOT,
                         env={**os.environ,'PL5_BRIDGE_PORT':str(port)},
                         stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    base=f'http://127.0.0.1:{port}/api/esse/meta-v33'
    try:
        for i in range(80):
            try:caps=_call(base+'/capabilities');break
            except OSError:time.sleep(.1)
        else:raise AssertionError('server did not start')
        assert len(caps['families'])==5
        body={'table':fixtures()['small_tree'].tolist(),'maximum':3}
        r=_call(base+'/learn',body)
        assert r['status']=='exact_compressed'
        assert r['abilities'][0]['proof']['checked_pairs']==100
        try:_call(base+'/learn',{'table':[[0]*10]*10,'bad':'injected'})
        except HTTPError as e:assert e.code==422
        else:raise AssertionError('unknown field accepted')
        try:_call(base+'/learn',{'table':[['__import__("os")']*10]*10})
        except HTTPError as e:assert e.code==422
        else:raise AssertionError('code accepted')
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
