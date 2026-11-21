"""V3.7.20 triple-gated research: reproducibility, leakage and tamper resistance."""
import json
from pathlib import Path

import numpy as np
import pytest

from pailie5.math_discovery_v3720 import (
    VERSION, read_cells, invent_compositions, propose, freeze, evaluate,
    split_synthetic,
)
from pailie5.structure_search_v372 import CellDataset
from pailie5.structure_ast_v372 import validate_ast


def fixture(tmp_path, case='composite_absproduct', seed=3720):
    d=tmp_path/'input'
    split_synthetic(d, case=case, seed=seed)
    return d, read_cells(d/'training.json'), read_cells(d/'validation.json'), read_cells(d/'holdout.json')


def study(tmp_path, *, case='composite_absproduct'):
    d, training, validation, holdout=fixture(tmp_path,case=case)
    p=tmp_path/'study'
    prop=propose(training,p,seed=3720,eval_budget=120,top_n=5)
    return d,p,prop,training,validation,holdout


def test_demo_split_and_schema(tmp_path):
    d,t,v,h=fixture(tmp_path)
    assert len(t.rows)==60 and len(v.rows)==len(h.rows)==20
    assert not (set(t.pairs)&set(v.pairs)|set(t.pairs)&set(h.pairs)|set(v.pairs)&set(h.pairs))
    assert len(set(t.pairs)|set(v.pairs)|set(h.pairs))==100
    assert json.loads((d/'protocol.json').read_text())['schema']==VERSION+':demo'


def test_split_deterministic_across_folders(tmp_path):
    d1=tmp_path/'a';d2=tmp_path/'b'
    split_synthetic(d1);split_synthetic(d2)
    for name in ('training.json','validation.json','holdout.json','protocol.json'):
        assert (d1/name).read_bytes()==(d2/name).read_bytes()


def test_demo_is_append_only(tmp_path):
    d=tmp_path/'input';split_synthetic(d)
    with pytest.raises(FileExistsError):split_synthetic(d)


def test_unknown_case_and_bad_seed_rejected(tmp_path):
    with pytest.raises(ValueError):split_synthetic(tmp_path/'a',case='uncontrolled_external')
    with pytest.raises(ValueError):split_synthetic(tmp_path/'b',seed=True)


def test_malformed_cells_rejected(tmp_path):
    p=tmp_path/'data.json'
    for bad in ('{"rows":[]}', '[[0,0,1],[0,0,2]]', '[[0,0,10]]',
                '[[0,0,true]]','[[0,0,1.5]]','[[0,0,"1"]]'):
        p.write_text(bad)
        with pytest.raises((ValueError,TypeError)):read_cells(p)


def test_generated_candidates_are_safe_and_repeatable(tmp_path):
    _,training,_,_=fixture(tmp_path)
    first=invent_compositions(training,top_n=8)
    second=invent_compositions(training,top_n=8)
    assert first==second
    assert first['proposal_count']>5000
    assert first['distinct_behaviours']>100
    assert first['labels_used']=='training_only'
    assert first['records'][0]['training_errors']==0
    assert all(validate_ast(expr) for expr in first['expressions'])


def test_limit_topn_and_budget_rejected(tmp_path):
    _,training,_,_=fixture(tmp_path)
    for top_n in (0,33,True):
        with pytest.raises(ValueError):invent_compositions(training,top_n=top_n)
    for budget in (0,99,True,10001):
        with pytest.raises(ValueError):propose(training,tmp_path/'bad',eval_budget=budget)


def test_three_gate_structured_full(tmp_path):
    _,p,prop,t,v,h=study(tmp_path)
    assert prop['holdout_read'] is False
    assert prop['predictive_advantage']=='NOT_ESTABLISHED'
    assert prop['generated']['distinct_behaviours']>100
    assert prop['candidates']
    f=freeze(p,v)
    assert f['test_labels_used'] is False
    assert f['selected']['validation_errors']==0
    result=evaluate(p,h)
    assert result['holdout_count']==20
    assert result['holdout_errors']==0
    assert result['holdout_accuracy']==1
    assert result['lottery_prediction_test'] is False
    assert result['production_enabled'] is False
    assert result['evidence_grade']=='EXPLORATORY_SYNTHETIC_ONLY'


def test_freeze_leakage_rejected(tmp_path):
    _,p,_,t,v,h=study(tmp_path)
    with pytest.raises(ValueError,match='leakage'):
        freeze(p,CellDataset((t.rows[0],)))
    assert not (p/'freeze.json').exists()


def test_holdout_overlaps_training_or_validation_rejected(tmp_path):
    _,p,_,t,v,h=study(tmp_path)
    freeze(p,v)
    for dataset in (CellDataset((t.rows[0],)),CellDataset((v.rows[0],))):
        with pytest.raises(ValueError, match='overlap'):
            evaluate(p,dataset)


def test_freeze_duplicate_rejected(tmp_path):
    _,p,_,t,v,h=study(tmp_path)
    freeze(p,v)
    with pytest.raises(FileExistsError):freeze(p,v)
    evaluate(p,h)
    with pytest.raises(FileExistsError):evaluate(p,h)


def test_proposal_tamper_detected(tmp_path):
    _,p,_,t,v,h=study(tmp_path)
    target=p/'proposal.json'
    data=json.loads(target.read_text());data['seed']+=1
    target.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='corrupted'):
        freeze(p,v)


def test_frozen_winner_tamper_detected(tmp_path):
    _,p,_,t,v,h=study(tmp_path)
    freeze(p,v)
    o=p/'final_operator.json'
    data=json.loads(o.read_text());data['operator']['operator_id']='0'*64
    o.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='integrity'):
        evaluate(p,h)


def test_frozen_manifest_tamper_detected(tmp_path):
    _,p,_,t,v,h=study(tmp_path)
    freeze(p,v)
    target=p/'freeze.json';data=json.loads(target.read_text());data['selected']['operator_id']='0'*64
    target.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='corrupted'):
        evaluate(p,h)


def test_holdout_mutation_cannot_change_frozen_selection(tmp_path):
    _,p,_,t,v,h=study(tmp_path)
    orig=freeze(p,v)
    prior=(p/'final_operator.json').read_bytes()
    counterfeit=CellDataset(tuple((a,b,(y+1)%10) for a,b,y in h.rows))
    score=evaluate(p,counterfeit)
    assert score['holdout_errors']>=10
    assert prior==(p/'final_operator.json').read_bytes()
    assert orig['selected']['operator_id']==score['operator_id']


def test_null_control_is_not_mistaken_for_prediction(tmp_path):
    _,p,prop,t,v,h=study(tmp_path,case='iid_null')
    freeze(p,v)
    result=evaluate(p,h)
    assert result['evidence_grade']=='EXPLORATORY_SYNTHETIC_ONLY'
    assert result['lottery_prediction_test'] is False
    assert result['predictive_advantage']=='NOT_ESTABLISHED'
    assert result['holdout_accuracy']<=0.6


def test_train_only_api_does_not_take_hidden_labels(tmp_path):
    _,p,_,_,_,_=study(tmp_path)
    import inspect
    sig=inspect.signature(propose)
    assert 'validation' not in sig.parameters and 'holdout' not in sig.parameters
    assert not (p/'freeze.json').exists()
    assert not (p/'evaluation.json').exists()


def test_stage_can_be_loaded_in_fresh_process(tmp_path):
    # Artifacts use JSON, not in-memory interpreter state.
    _,p,prop,t,v,h=study(tmp_path)
    del t,prop
    frozen=freeze(Path(str(p)),CellDataset(tuple(v.rows)))
    result=evaluate(Path(str(p)),CellDataset(tuple(h.rows)))
    assert frozen['selected']['operator_id']==result['operator_id']


def test_no_eval_or_generated_python_execution():
    from pailie5.structure_ast_v372 import load_ast
    with pytest.raises(ValueError):load_ast(['binary','__import__',['a'],['b']])
    with pytest.raises(ValueError):load_ast(['binary','add',['a'],['binary','malicious',['a'],['b']]])
