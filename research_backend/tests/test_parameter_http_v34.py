import json,os,socket,subprocess,sys,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1]
def call(url,payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=Request(url,data=data,headers={'Content-Type':'application/json'} if data else {})
    with urlopen(req,timeout=30) as response:return json.load(response)

def test_http_training_scoped_no_writes():
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    proc=subprocess.Popen([sys.executable,'integration_server.py'],cwd=ROOT,
                          env={**os.environ,'PL5_BRIDGE_PORT':str(port)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    base=f'http://127.0.0.1:{port}/api/esse/parameters-v34'
    try:
        for _ in range(70):
            try:catalog=call(base+'/catalog');break
            except OSError:time.sleep(.1)
        else:raise AssertionError('HTTP did not start')
        assert catalog['counts']['trained_v34']==4
        history=[x*17%100000 for x in range(200)]
        result=call(base+'/fit',{'kind':'step','history':history})
        assert len(result['threshold_candidates'])==9
        lift=call(base+'/fit',{'kind':'lift','history':history,'first_pos':0,'second_pos':1})
        assert lift['trial_count']==100
        assert lift['predictive_advantage']=='NOT_ESTABLISHED'
        for attack in ({'kind':'step','history':[0]*200,'__import__':'os'},
                       {'kind':'step','history':['00000']*200},
                       {'kind':'lift','history':[0]*200,'first_pos':True}):
            try:call(base+'/fit',attack)
            except HTTPError as e:assert e.code==422
            else:raise AssertionError('invalid input accepted')
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
