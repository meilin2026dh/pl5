import json, subprocess, sys
from pathlib import Path
from datetime import datetime,timezone
from test_forward_sculpt_v152 import request,rows
from snapshot_v15 import OFFICIAL_URL

ROOT=Path(__file__).resolve().parents[1]

def test_cli_seal_settle_report_with_official_format_fixture(tmp_path):
    db=tmp_path/'evidence.db'; cache=tmp_path/'cache.json';req=tmp_path/'request.json'
    req.write_text(json.dumps(request()),encoding='utf8')
    base={'sourceUrl':OFFICIAL_URL,'updatedAt':datetime.now(timezone.utc).isoformat(),
          'draws':rows()}
    cache.write_text(json.dumps(base),encoding='utf8')
    def cli(*argv):
        return subprocess.run([sys.executable,'research_v152.py','--db',str(db),*argv],cwd=ROOT,
                              capture_output=True,text=True)
    x=cli('seal','--cache',str(cache),'--request',str(req),'--target','26291',
          '--source','synthetic official-like sample')
    assert x.returncode==0,x.stderr
    seal=json.loads(x.stdout);assert seal['count']==100
    assert json.loads(cli('report').stdout)['pending']==1
    # Future known draw cannot be re-sealed.
    base['draws'].append({'issue':'26291','date':'2026-11-01','number':'00150'})
    cache.write_text(json.dumps(base),encoding='utf8')
    assert cli('seal','--cache',str(cache),'--request',str(req),'--target','26291',
               '--source','synthetic official-like sample').returncode==2
    y=cli('settle','--cache',str(cache),'--source','synthetic official-like sample')
    assert y.returncode==0,y.stderr
    assert json.loads(y.stdout)['newly_settled']==1
    report=json.loads(cli('report').stdout)
    assert report['integrity']['ok'] and report['settled']==1
