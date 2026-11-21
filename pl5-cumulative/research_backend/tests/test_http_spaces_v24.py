"""HTTP boundary tests, with live loopback server and no external API calls."""
from __future__ import annotations
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]

def _json(url,payload=None):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
    req=Request(url,data=data,headers={'Content-Type':'application/json'} if data is not None else {},
                method='POST' if data is not None else 'GET')
    with urlopen(req,timeout=15) as fh:return json.load(fh)

def test_spaces_v24_loopback():
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    env={**os.environ,'PL5_BRIDGE_PORT':str(port)}
    proc=subprocess.Popen([sys.executable,'integration_server.py'],cwd=ROOT,env=env,
                          stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    base=f'http://127.0.0.1:{port}/api/esse'
    try:
        for _ in range(50):
            try:
                caps=_json(base+'/spaces-v24/capabilities');break
            except OSError: time.sleep(.1)
        else:raise AssertionError('本地HTTP服务启动失败')
        assert len(caps['capabilities'])==9
        assert caps['predictive_advantage']=='UNVERIFIED'
        result=_json(base+'/spaces-v24/evaluate',{
            'history':['00011']*5,
            'rules':[{'name':'ban0','family':'sum_span','metric':'sum','op':'eq','value':0}],
            'temporal_specs':[{'name':'repeat2','family':'sum_span','metric':'sum','window':4,'pattern':'repeat'}],
            'budget':10,
        })
        assert result['active_temporal_rules']==1
        assert result['strict_remaining']<100000
        assert len(result['ranked_numbers'])==10
        assert '00000' not in result['strict_numbers']
        try:
            _json(base+'/spaces-v24/evaluate',{'history':[],'budget':1000000})
            assert False,'无效预算必须拒绝'
        except HTTPError as e: assert e.code==422
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
