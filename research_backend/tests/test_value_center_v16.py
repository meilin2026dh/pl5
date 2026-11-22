"""Value center uses only immutable original evidence, no score-as-probability."""
import json
import sqlite3
from pailie5.forward_sculpt_v152 import SculptLedger
from pailie5.value_center_v16 import analyze
from status_v151 import status
from test_forward_sculpt_v152 import seal, rows


def settled_one(path):
    with SculptLedger(path) as ledger:
        seal(ledger)
        ledger.settle(official_draws=rows()+[{'issue':'26291','date':'2026-11-01','number':'00150'}],
                      source_label='synthetic format fixture')


def test_missing_never_creates_database(tmp_path):
    path=tmp_path/'does-not-exist.db'
    assert analyze(path)['state']=='file_missing'
    assert not path.exists()
    assert analyze(None)['state']=='not_configured'


def test_readonly_per_knife_expected_observed_and_uniqueness(tmp_path):
    path=tmp_path/'ledger.db';settled_one(path)
    before=path.stat().st_mtime_ns
    r=analyze(path)
    assert r['state']=='ready' and r['integrity_verified'] is True
    assert r['used_settled_prefix']==1 and r['total_sealed']==1
    assert r['automatic_activation'] is False and r['real_win_probabilities'] is False
    a,b={x['id']:x for x in r['knives']}.values()
    assert set(x['id'] for x in r['knives'])=={'a','b'}
    assert a['expected_fair_wrong_cuts']==150/100000
    assert b['expected_fair_wrong_cuts']==100/100000
    assert a['observed_wrong_cuts']==0 and b['observed_wrong_cuts']==1
    assert b['first_cut_actual']==1 and b['unique_wrong_cuts']==1
    assert a['proposed_research_weight']==1.0 and b['proposed_research_weight']==1.0
    assert r['report_sha256']==analyze(path)['report_sha256']
    assert path.stat().st_mtime_ns==before
    s=status(forward_db_path=path)
    assert s['value_center']['state']=='ready'


def test_tamper_blocks_value_report(tmp_path):
    path=tmp_path/'ledger.db';settled_one(path)
    with sqlite3.connect(path) as db:
        db.execute('DROP TRIGGER seals_no_update')
        db.execute("UPDATE seals SET receipt_sha256=?",('f'*64,))
        db.commit()
    r=analyze(path)
    assert r['state']=='ledger_invalid'
    assert r['knives']==[]


def test_unsettled_records_do_not_influence_value_analysis(tmp_path):
    path=tmp_path/'ledger.db';settled_one(path)
    before=analyze(path)
    with SculptLedger(path) as ledger:
        from test_forward_sculpt_v152 import request
        seal(ledger,nums=rows()+[{'issue':'26291','date':'2026-11-01','number':'00150'}],
             req=request('26291'),target='26292')
    after=analyze(path)
    assert after['used_settled_prefix']==1 and after['pending_after_prefix']==1
    assert after['knives']==before['knives']
    assert after['latest_settled_issue']=='26291'


def test_invalid_parameters_raise(tmp_path):
    import pytest
    for kw in [{'minimum_periods':0},{'minimum_periods':3010},
               {'alpha':0},{'alpha':1},{'max_periods':2}]:
        with pytest.raises(ValueError):analyze(None,**kw)


def test_dynamic_research_weights_bounded_and_neutral_on_low_evidence():
    from pailie5.value_center_v16 import propose_research_weight as proposal
    a=proposal(periods=20,observed=0,expected=12.0,novelty=1,
               minimum_periods=100,family_size=5,alpha=.01)
    assert a['weight']==1.0 and a['category']=='insufficient_evidence'
    good=proposal(periods=200,observed=2,expected=100.0,novelty=.5,
               minimum_periods=100,family_size=5,alpha=.01)
    bad=proposal(periods=200,observed=198,expected=100.0,novelty=1,
               minimum_periods=100,family_size=5,alpha=.01)
    assert good['category']=='fewer_wrong_cuts' and 1<good['weight']<=1.1
    assert bad['category']=='more_wrong_cuts' and .8<=bad['weight']<1
    # Geometrically redundant knife must not get rewarded for old observations.
    redundant=proposal(periods=200,observed=2,expected=100.0,novelty=0,
                       minimum_periods=100,family_size=5,alpha=.01)
    assert redundant['weight']==1.0


def test_cli_readonly_report(tmp_path):
    import subprocess,sys
    from pathlib import Path
    path=tmp_path/'ledger.db';settled_one(path)
    backend=Path(__file__).resolve().parents[1]
    output=tmp_path/'report.json'
    result=subprocess.run([sys.executable, 'research_v16.py', '--db',str(path),
                           '--output',str(output)],cwd=backend,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    parsed=json.loads(output.read_text(encoding='utf8'))
    assert parsed['used_settled_prefix']==1
    assert len(parsed['research_queue'])==2
    assert parsed['report_sha256']==json.loads(result.stdout)['report_sha256']
