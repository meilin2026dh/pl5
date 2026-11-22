"""Loopback integration, no internet, no external application updates."""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]

def _fetch(url,payload=None):
    buf=json.dumps(payload).encode() if payload is not None else None
    req=Request(url,data=buf,headers={'Content-Type':'application/json'} if buf else {},
                method='POST' if buf is not None else 'GET')
    with urlopen(req,timeout=16) as res:return json.load(res)

def test_spaces_v25_loopback(tmp_path):
    s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close()
    env={**os.environ,'PL5_BRIDGE_PORT':str(port),'PL5_REPRESENTATION_DB':str(tmp_path/'inventory.sqlite')}
    proc=subprocess.Popen([sys.executable,'integration_server.py'],cwd=ROOT,env=env,
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    base=f'http://127.0.0.1:{port}/api/esse/spaces-v25'
    try:
        for _ in range(80):
            try:
                caps=_fetch(base+'/capabilities');break
            except OSError:time.sleep(.1)
        else:raise AssertionError('服务未启动')
        assert caps['version']=='v2.5'
        assert caps['automatic_promotion'] is False
        r=_fetch(base+'/discover',{'seed':10,'count':4})
        assert r['candidate_audit']['reviewed'][0]['capability']['registration']=='research_candidate'
        history=[f'{(i*7919+i*i*17)%100000:05d}' for i in range(120)]
        t=_fetch(base+'/discover',{'seed':11,'count':8,'history':history,'test_periods':20})
        assert t['historical_holdout']['periods']==20
        assert len(t['next_draw_random_control_100'])==100
        for invalid in [{'seed':-1,'count':10},{'count':500},{'history':['1234']*100,'count':5}]:
            try:_fetch(base+'/discover',invalid)
            except HTTPError as exc:assert exc.code==422
            else:raise AssertionError('bad input was accepted')
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
