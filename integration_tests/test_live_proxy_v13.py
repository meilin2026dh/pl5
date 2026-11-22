"""Run the actual Node same-origin proxy against the actual Python ESSE HTTP process."""
from __future__ import annotations
from pathlib import Path
import json, os, subprocess, sys, time, urllib.request
import numpy as np
BASE=Path(__file__).resolve().parents[1]
BACKEND=BASE/'research_backend'
sys.path.insert(0,str(BACKEND))
from pailie5.github_rule_parity import evaluate_basic
from pailie5.integration_bridge import encode_mask

def test():
  env={**os.environ,'PL5_BRIDGE_PORT':'18765','PYTHONPATH':str(BACKEND)}
  node_code='''import {createServer} from 'node:http';
import {handleEsseProxy} from './github_overlay/server/esseProxy.mjs';
createServer(async(req,res)=>await handleEsseProxy(req,res)).listen(18766,'127.0.0.1');'''
  py=subprocess.Popen([sys.executable,'-u',str(BACKEND/'integration_server.py')],env=env,
       stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  js=subprocess.Popen(['node','--input-type=module','-e',node_code],cwd=BASE,env=env,
       stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  try:
    for i in range(50):
      try:
        with urllib.request.urlopen('http://127.0.0.1:18766/api/esse/health',timeout=1) as f:
          assert f.status==200
        break
      except Exception:
        time.sleep(.1)
    else:raise AssertionError('services failed to start')
    spec={'id':'sum10','kind':'sum','mode':'include','values':[10]}
    m=evaluate_basic(spec)
    payload={'schema':'pl5-esse-bridge-v1','protocol_upgrade':'v13_verified',
        'combination':'strict','k':30,'seed':20261101,
        'base':encode_mask(np.ones(100000,dtype=bool)),
        'rules':[{'id':'sum10','label':'sum','group':'sum','enabled':True,
             'rule_spec':spec,'kept':encode_mask(m)}],
        'strict_kept':encode_mask(m),
        'expected_strict_keep':int(m.sum())}
    request=urllib.request.Request('http://127.0.0.1:18766/api/esse/sculpt',
       data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(request,timeout=20) as resp:
      result=json.load(resp)
    assert result['full_mask_parity_verified'] is True
    assert result['independent_rule_count']==1
    assert result['source_guard'] is True
    assert result['selected_count']==30
    print('HTTP Node→Python V1.3: verified 30 candidates, full-mask parity & independent basic-rule parity')
  finally:
    js.terminate();py.terminate()
    for p in [js,py]:
      try:p.wait(timeout=3)
      except subprocess.TimeoutExpired:p.kill()
if __name__=='__main__':test()
