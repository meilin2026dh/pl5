"""V3.7.21 meta-operator: failures, leakage, abstention and reproducibility."""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from pailie5.structure_search_v372 import CellDataset
from pailie5.structure_ast_v372 import validate_ast, table
from pailie5.structure_evidence_v372 import load_operator
from pailie5.math_discovery_v3720 import read_cells
from pailie5.meta_operator_v3721 import (
    make_synthetic, fibre_diagnostics, invent_meta_operators, propose, freeze, evaluate,
)


def case(tmp_path, name='square_sum', seed=3721):
    data = tmp_path/'data'
    make_synthetic(data, case=name, seed=seed)
    train, val, test = [read_cells(data/f'{stage}.json')
                        for stage in ('training', 'validation', 'holdout')]
    return data, train, val, test


def prepared(tmp_path, name='square_sum', seed=3721):
    data, train, val, test = case(tmp_path,name,seed)
    work = tmp_path/'study'
    proposal = propose(train,work)
    return work,train,val,test,proposal


def test_known_square_problem_repaired(tmp_path):
    work,train,val,test,prop = prepared(tmp_path)
    assert prop['baseline_training_errors'] > 0
    assert min(c['training_errors'] for c in prop['candidates']) == 0
    assert prop['holdout_read'] is False
    assert any(c['legacy_error_repairs'] > 0 for c in prop['candidates'] if c['learned_meta'])
    frozen = freeze(work,val)
    assert frozen['status'] == 'FROZEN'
    assert frozen['test_labels_used'] is False
    result = evaluate(work,test)
    assert result['status']=='EVALUATED' and result['holdout_errors']==0
    assert result['evidence_grade']=='DEVELOPMENT_SYNTHETIC_ONLY'
    assert result['predictive_advantage']=='NOT_ESTABLISHED'
    assert result['production_enabled'] is False


@pytest.mark.parametrize('seed',[3721,3722,3723,3724,3725])
@pytest.mark.parametrize('name',['square_sum','quadratic_difference'])
def test_multi_seed_structured_transfer(tmp_path,name,seed):
    work,train,val,test,prop=prepared(tmp_path,name,seed)
    f=freeze(work,val)
    assert f['status']=='FROZEN', (seed, name, f['abstention_reason'])
    e=evaluate(work,test)
    assert e['holdout_errors']==0, (name,seed,e)


def test_linear_old_rule_remains_correct(tmp_path):
    work,t,v,h,proposal=prepared(tmp_path,'linear_sum')
    assert proposal['baseline_training_errors']==0
    f=freeze(work,v)
    assert f['status']=='FROZEN'
    assert f['selected']['name']=='legacy_composition'
    assert evaluate(work,h)['holdout_errors']==0


@pytest.mark.parametrize('seed',[3721,3722,3723,3724,3725])
def test_random_null_abstains_without_scoring(tmp_path,seed):
    work,t,v,h,proposal=prepared(tmp_path,'iid_null',seed)
    f=freeze(work,v)
    assert f['status']=='ABSTAIN'
    assert not (work/'final_operator.json').exists()
    e=evaluate(work,h)
    assert e['status']=='ABSTAIN' and e['holdout_errors'] is None
    assert e['no_holdout_scoring'] is True


def test_function_fibres_depend_only_on_training(tmp_path):
    _,t,v,h=case(tmp_path)
    diagnostics=fibre_diagnostics(t)
    assert any(r['feature']=='sum' and r['eligible'] for r in diagnostics)
    assert len(diagnostics)>=10
    sig=inspect.signature(invent_meta_operators)
    assert 'validation' not in sig.parameters and 'holdout' not in sig.parameters
    sig2=inspect.signature(propose)
    assert 'validation' not in sig2.parameters and 'holdout' not in sig2.parameters


def test_new_operator_expression_is_old_safe_grammar(tmp_path):
    work,t,v,h,report=prepared(tmp_path)
    metacards=[card for card in report['candidates'] if card['learned_meta']]
    assert metacards
    for card in metacards:
        op=load_operator(work/card['path'])
        nodes,depth=validate_ast(op.expression)
        assert nodes<=15 and depth<=8
        assert card['learned_meta']['second_difference_mod10'] in range(10)
        u,vv,w=card['learned_meta']['coefficients']
        vals=card['learned_meta']['unary_lookup_mod10']
        assert all((vals[i+2]-2*vals[i+1]+vals[i])%10 == (2*u)%10
                   for i in range(8))


def test_repeat_is_deterministic(tmp_path):
    _,t,v,h=case(tmp_path)
    a,b=propose(t,tmp_path/'a'),propose(t,tmp_path/'b')
    assert a==b
    assert (tmp_path/'a/proposal.json').read_bytes()==(tmp_path/'b/proposal.json').read_bytes()
    assert freeze(tmp_path/'a',v)==freeze(tmp_path/'b',v)
    assert evaluate(tmp_path/'a',h)==evaluate(tmp_path/'b',h)


def test_no_duplicate_proposal_freeze_evaluation(tmp_path):
    w,t,v,h,_=prepared(tmp_path)
    with pytest.raises(FileExistsError):propose(t,w)
    freeze(w,v)
    with pytest.raises(FileExistsError):freeze(w,v)
    evaluate(w,h)
    with pytest.raises(FileExistsError):evaluate(w,h)


def test_leakage_rejected_between_each_gate(tmp_path):
    w,t,v,h,_=prepared(tmp_path)
    with pytest.raises(ValueError,match='leakage'):
        freeze(w,CellDataset((t.rows[0],)))
    freeze(w,v)
    with pytest.raises(ValueError,match='overlap'):
        evaluate(w,CellDataset((v.rows[0],)))
    with pytest.raises(ValueError,match='overlap'):
        evaluate(w,CellDataset((t.rows[0],)))
    assert not (w/'evaluation.json').exists()


def test_proposal_modification_detected(tmp_path):
    w,t,v,h,_=prepared(tmp_path)
    path=w/'proposal.json'; raw=json.loads(path.read_text())
    raw['hypothesis_count']+=1
    path.write_text(json.dumps(raw),encoding='utf8')
    with pytest.raises(ValueError,match='integrity'):
        freeze(w,v)


def test_operator_tamper_detected_before_freeze(tmp_path):
    w,t,v,h,report=prepared(tmp_path)
    path=w/report['candidates'][0]['path']
    raw=json.loads(path.read_text());raw['operator']['operator_id']='0'*64
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError,match='integrity'):
        freeze(w,v)


def test_frozen_winner_tamper_detected_before_evaluation(tmp_path):
    w,t,v,h,_=prepared(tmp_path)
    freeze(w,v)
    path=w/'final_operator.json';raw=json.loads(path.read_text())
    raw['operator']['operator_id']='0'*64
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError,match='integrity'):
        evaluate(w,h)


def test_abstention_threshold_must_be_bounded(tmp_path):
    w,t,v,h,_=prepared(tmp_path)
    with pytest.raises(ValueError):freeze(w,v,max_error_rate=1.0)
    with pytest.raises(ValueError):freeze(w,v,max_error_rate=True)
    assert not (w/'freeze.json').exists()


def test_validation_labels_do_not_change_train_proposals(tmp_path):
    _,t,v,h=case(tmp_path)
    a=invent_meta_operators(t)
    wrong=CellDataset(tuple((x,y,(z+5)%10) for x,y,z in v.rows))
    assert wrong.fingerprint != v.fingerprint
    b=invent_meta_operators(t)
    assert a==b
    assert a['source']=='training_only'


def test_no_untrusted_exec_or_eval(tmp_path):
    _,t,v,h=case(tmp_path)
    with pytest.raises(ValueError): invent_meta_operators(t,top_n=True)
    with pytest.raises(ValueError): invent_meta_operators(t,top_n=200)
    with pytest.raises(ValueError): make_synthetic(tmp_path/'bad',case='__import__',seed=1)

@pytest.mark.parametrize('seed',[3721,3722,3723,3724,3725])
def test_out_of_grammar_cubic_abstains(tmp_path,seed):
    w,t,v,h,_=prepared(tmp_path,'cubic_sum',seed)
    f=freeze(w,v)
    assert f['status']=='ABSTAIN'
    assert evaluate(w,h)['holdout_errors'] is None
