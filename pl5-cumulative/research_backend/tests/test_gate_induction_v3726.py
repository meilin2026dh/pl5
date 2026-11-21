"""V3.7.26 gate grammar + CPU-accountable external challenge handshake."""
import json
from pathlib import Path
import numpy as np
import pytest

from pailie5.structure_search_v372 import CellDataset
from pailie5.gate_induction_v3726 import (
    _predicate, predicate_specs, program_table, fit, freeze, evaluate, commit_holdout)
from research_external_challenge_v3726 import solve, grade
from research_open_grammar_v3725 import prepare


def split(table,seed=372603):
    y=np.asarray(table,dtype=np.int64).reshape(100)%10
    indices=np.random.default_rng(seed+61000).permutation(100)
    return [CellDataset(tuple((int(k//10),int(k%10),int(y[k])) for k in keys))
            for keys in (indices[:48],indices[48:64],indices[64:])]


def target(family):
    a,b=np.indices((10,10),dtype=np.int64)
    xor=np.bitwise_xor(a,b)
    if family=='diagonal':return np.where(a==b,a*b+3,xor+3)%10
    if family=='congruence':return np.where((a-b)%3==1,a*b+3,xor+3)%10
    if family=='threshold':return np.where(a+b>=10,a+3,xor+3)%10
    if family=='linear':return (a+b+3)%10
    if family=='random':return np.random.default_rng(372603).integers(0,10,(10,10))
    raise AssertionError('unknown fixture')


def test_predicate_is_finite_and_whitelisted():
    assert len(predicate_specs())==25
    assert np.count_nonzero(_predicate({'kind':'equal'}))==10
    assert np.count_nonzero(_predicate({'kind':'less'}))==45
    with pytest.raises(ValueError):_predicate({'kind':'exec','python':'__import__("os")'})
    with pytest.raises(ValueError):_predicate({'kind':'sum_ge','threshold':999})


@pytest.mark.parametrize('family',['diagonal','congruence','threshold','linear'])
def test_mathematical_families_holdout(family,tmp_path):
    tr,val,ho=split(target(family))
    nonce='this-is-a-private-long-nonce-for-test'
    record=fit(tr,tmp_path,holdout_digest=commit_holdout(ho,nonce))
    assert record['candidate_evaluations']==26
    fr=freeze(tmp_path,val)
    assert fr['status']=='FROZEN'
    assert evaluate(tmp_path,ho,nonce=nonce)['test_errors']==0


def test_random_noise_abstention(tmp_path):
    tr,val,ho=split(target('random'))
    fit(tr,tmp_path)
    assert freeze(tmp_path,val)['status']=='ABSTAIN'
    assert evaluate(tmp_path,ho)['status']=='ABSTAIN'


def test_deterministic_fit_spec_excluding_runtime(tmp_path):
    tr,val,ho=split(target('diagonal'))
    a=fit(tr,tmp_path/'first')
    b=fit(tr,tmp_path/'second')
    assert a['exact_fit_tables']==b['exact_fit_tables']
    assert a['candidate_evaluations']==b['candidate_evaluations']


def test_reject_bad_code_and_commitment(tmp_path):
    with pytest.raises(ValueError):program_table({'syntax':'induced_gate_mod10','predicate':{'kind':'equal'},'features':['evil()'],'coefficients':[1]})
    with pytest.raises(ValueError):program_table({'syntax':'induced_gate_mod10','predicate':None,'features':['a'],'coefficients':[1],'unknown':True})
    tr,val,ho=split(target('diagonal'))
    fit(tr,tmp_path,holdout_digest=commit_holdout(ho,'nonce-12345678901234567'))
    with pytest.raises(FileExistsError):fit(tr,tmp_path)
    with pytest.raises(ValueError,match='overlap'):freeze(tmp_path,tr)
    freeze(tmp_path,val)
    with pytest.raises(ValueError,match='commitment'):evaluate(tmp_path,ho,nonce='wrong-but-long-enough')
    evaluate(tmp_path,ho,nonce='nonce-12345678901234567')
    with pytest.raises(FileExistsError):evaluate(tmp_path,ho,nonce='nonce-12345678901234567')


def test_inprocess_external_interface_rehearsal(tmp_path):
    train,validation,holdout=split(target('diagonal'))
    challenge=tmp_path/'issuer_challenge.json'
    challenge.write_text(json.dumps({'task_id':'independent_issuer_sample','source_description':'DEVELOPER_FIXTURE_NOT_EXTERNAL',
        'train':[list(x) for x in train.rows],'validation':[list(x) for x in validation.rows],
        'holdout':[list(x) for x in holdout.rows]}),encoding='utf-8')
    pub=tmp_path/'public';priv=tmp_path/'private';result=tmp_path/'solver'
    prepare(challenge,pub,priv)
    public_file=pub/'public_challenge.json';private_file=priv/'private_challenge.json'
    assert 'holdout' not in json.loads(public_file.read_text(encoding='utf-8'))
    assert 'nonce' not in public_file.read_text(encoding='utf-8')
    output=solve(public_file,result)
    assert output['methods']['v3726_gate']=='FROZEN'
    assert not (result/'private_challenge.json').exists()
    r=grade(public_file,private_file,result)
    assert r['issuer_holdout_commitment_verified'] is True
    assert r['methods']['v3726_gate']['errors']==0
    assert r['independent_external_blind_verified'] is False
    with pytest.raises(FileExistsError):grade(public_file,private_file,result)


def test_issuer_tamper_and_model_freeze_tamper(tmp_path):
    tr,val,ho=split(target('diagonal'))
    challenge=tmp_path/'task.json'
    challenge.write_text(json.dumps({'task_id':'test002','source_description':'self-reported',
       'train':[list(x) for x in tr.rows], 'validation':[list(x) for x in val.rows],
       'holdout':[list(x) for x in ho.rows]}))
    prepare(challenge,tmp_path/'pub',tmp_path/'priv')
    pub=tmp_path/'pub'/'public_challenge.json'
    pri=tmp_path/'priv'/'private_challenge.json'
    solve(pub,tmp_path/'solved')
    body=json.loads(pri.read_text());body['holdout'][0][2]=(body['holdout'][0][2]+1)%10
    pri.write_text(json.dumps(body))
    with pytest.raises(ValueError,match='commitment'):grade(pub,pri,tmp_path/'solved')


def test_paired_budget_protocol_invariants():
    from benchmark_gate_induction_v3726 import FAMILIES,SEEDS,ARMS,BUDGETS_MS
    assert len(FAMILIES)*len(SEEDS)==50
    assert len(ARMS)==3
    assert tuple(sorted(BUDGETS_MS))==BUDGETS_MS


def test_portfolio_selects_only_before_holdout():
    from benchmark_gate_induction_v3726 import portfolio_choice
    from pailie5.open_grammar_v3725 import _features, _stage_names
    old={'status':'ABSTAIN','selected':None}
    new={'status':'ABSTAIN','selected':None}
    assert portfolio_choice(old,new) is None
    assert portfolio_choice({'status':'FROZEN','selected':{'spec':{}}},new)=='v3725_ring'
    assert portfolio_choice(old,{'status':'FROZEN','selected':{'spec':{}}})=='v3726_gate'
