import hashlib
import json
import math
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from autoresearch.formulas import InventedAlgorithm
from autoresearch.novelty_v07 import assess_novelty, invent_diverse, signature
from autoresearch.paper_protocol_v07 import build_research_protocol
from autoresearch.prospective import settle_from_history
from autoresearch.forward_v07 import (_mixture_e_value, _poisson_binomial_tail,
                                            forward_report,freeze_checked,verify_commitments)
from autoresearch.store import LabStore
from autoresearch.registry_v06 import ResearchRegistry
from research_v07 import main


def formula(metric='sum',pattern='constant'):
    return InventedAlgorithm({'kind':'metric','name':metric},pattern,3,'paper01','study')


def fake_frame():
    return pd.DataFrame({'period':['202610001','202610002'], 'number':['00001','00002']})


def freeze(db,target,nums,frame=None):
    return freeze_checked(db,draws_frame=frame if frame is not None else fake_frame(),
       target_period=target,candidates=nums,history_sha256='a'*64,
       algorithm_sha256='b'*64,official_source='official:test-not-verified')


def test_formula_signature_detects_exact_equivalence():
    a=formula('sum');b=formula('sum','strict_up')
    info=assess_novelty(a,[b])
    assert not info['is_novel_by_heuristic']
    assert '逐项相同' in info['rejection_reasons'][0]
    assert signature(a)[0]['unique_states']>1


def test_novelty_filters_constant_metric():
    c=InventedAlgorithm({'kind':'const','value':2},'constant',3,'paper','test')
    r=assess_novelty(c,[])
    assert r['unique_states']==1 and not r['is_novel_by_heuristic']


def test_new_metrics_screening_respects_limit_and_budget():
    new,report=invent_diverse('time series random process change point',
                              'paper01',limit=2,search_budget=8)
    assert len(new)<=2 and report['evaluated']<=8
    assert len(set(signature(x)[0]['formula_signature'] for x in new))==len(new)
    with pytest.raises(ValueError):invent_diverse('a','b',limit=20)


def test_paper_protocol_cautions_about_abstract():
    p={'doc_key':'a','title':'A paper','kind':'abstract',
       'text_excerpt':'Study of sequential probability methods using calibration and testing',
       'source_url':'https://example.org/paper'}
    report=build_research_protocol(p)
    assert not report['paper_method_reproduced']
    assert not report['full_text_read']
    assert any('摘要' in x for x in report['uncertainties'])


def test_bernoulli_e_martingale_one_step_exact():
    e1=_mixture_e_value([{'k':100,'hit':True}])['e_value']
    e0=_mixture_e_value([{'k':100,'hit':False}])['e_value']
    assert math.isclose(.001*e1+.999*e0,1.,abs_tol=1e-8)
    assert e1>e0


def test_poisson_binomial_variable_k():
    p=[.1,.2]
    assert _poisson_binomial_tail(p,0)==1
    assert math.isclose(_poisson_binomial_tail(p,1),.28)
    assert math.isclose(_poisson_binomial_tail(p,2),.02)


def test_freeze_prevents_target_already_in_history(tmp_path):
    conn=sqlite3.connect(tmp_path/'p.sqlite')
    with pytest.raises(ValueError):freeze(conn,'202610002',['00001'])
    a=freeze(conn,'202610003',['00001','00002'])
    assert a['immutable']
    with pytest.raises(ValueError):freeze(conn,'202610003',['00003'])
    assert verify_commitments(conn)['all_hashes_intact']
    conn.close()


def test_forward_no_hit_baseline_and_e_value(tmp_path):
    conn=sqlite3.connect(tmp_path/'p.sqlite')
    for i in range(3,13):freeze(conn,f'202610{i:03d}',['00001']*0+['00099'])
    result=settle_from_history(conn,period_to_number={f'202610{i:03d}':'00001' for i in range(3,13)},
                               data_sha256='e'*64,source_description='official:test')
    assert result['newly_settled']==10
    report=forward_report(conn)
    assert report['auditable_contiguous_prefix']==10
    assert report['observed_hits_in_prefix']==0
    assert math.isclose(report['expected_fair_hits_in_prefix'],.0001)
    assert len(report['nonoverlapping_10_record_blocks'])==1
    assert report['anytime_e_evidence']['e_value']<1
    conn.close()


def test_pending_gap_suppresses_later_settlements(tmp_path):
    conn=sqlite3.connect(tmp_path/'p.sqlite')
    freeze(conn,'202610003',['00000']);freeze(conn,'202610004',['00000'])
    settle_from_history(conn,period_to_number={'202610004':'00000'},
                        data_sha256='d'*64,source_description='official:test')
    x=forward_report(conn)
    assert x['auditable_contiguous_prefix']==0
    assert x['settled_after_pending_not_counted']==1
    assert x['anytime_e_evidence'] is None
    conn.close()


def test_commitment_corruption_detected(tmp_path):
    conn=sqlite3.connect(tmp_path/'p.sqlite');freeze(conn,'202610003',['00001'])
    conn.execute('DROP TRIGGER predictions_no_update')
    conn.execute("UPDATE predictions SET candidates_json='[\"00002\"]' WHERE target_period='202610003'")
    assert not verify_commitments(conn)['all_hashes_intact']
    assert forward_report(conn)['fixed_horizon_p_value_unadjusted'] is None
    conn.close()


def test_v07_cli_paper_and_discovery(tmp_path,capsys):
    db=str(tmp_path/'lab.sqlite')
    with LabStore(db) as store:
        reg=ResearchRegistry(store.db)
        reg.add_document('x','Research paper',
             'Statistical work in online sequences, information entropy and distribution change')
    assert main(['--db',db,'paper-plan','--key','x'])==0
    payload=json.loads(capsys.readouterr().out)
    assert payload['paper_method_reproduced'] is False
    assert main(['--db',db,'discover','--key','x','--limit','1'])==0
    payload=json.loads(capsys.readouterr().out)
    assert payload['auto_activated'] is False


def test_no_retrospective_backfill_below_existing_target(tmp_path):
    conn=sqlite3.connect(tmp_path/'ledger.sqlite')
    freeze(conn,'202610010',['10000'])
    with pytest.raises(ValueError,match='严格递增'):
        freeze(conn,'202610009',['20000'])
    conn.close()


def test_forward_single_exact_hit_has_known_likelihood(tmp_path):
    conn=sqlite3.connect(tmp_path/'ledger.sqlite')
    freeze(conn,'202610003',['00012']*0+['00088'])
    settle_from_history(conn,period_to_number={'202610003':'00088'},
         data_sha256='f'*64,source_description='official:test')
    r=forward_report(conn)
    assert r['observed_hits_in_prefix']==1
    assert math.isclose(r['fixed_horizon_p_value_unadjusted'],1/100000)
    assert r['anytime_e_evidence']['e_value']>1
    conn.close()
