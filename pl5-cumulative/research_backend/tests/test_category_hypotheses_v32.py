"""V3.2 category hypothesis generation, exact verification, and scientific limits."""
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from pailie5.category_hypotheses_v32 import (
    CategoryHypothesis, HypothesisRegistry, infer_new_categories,
    study_historical_operators, synthetic_fixtures,
)
from pailie5.primitive_categories_v31 import compose_abilities,run_operator_on_100k


@pytest.fixture(scope='module')
def inputs():
    return synthetic_fixtures()


def test_piecewise_row_states_created_and_independently_certified(inputs):
    t=inputs['two_state_piecewise']
    r=infer_new_categories(t)
    op=next(x for x in r['abilities'] if x.family=='piecewise_orbit')
    assert op.payload['orientation'] in ('sum','difference')
    assert len(op.payload['orbits'])==2
    assert op.representation_bits==75
    assert np.array_equal(op.table(),t)
    assert op.certify()['checked_pairs']==100
    assert op.card()['status']=='research_only'


def test_affine_family_not_just_old_sum_difference(inputs):
    t=inputs['affine_modular']
    r=infer_new_categories(t)
    op=next(x for x in r['abilities'] if x.family=='affine_orbit')
    assert op.representation_bits==52
    assert r['old_best_bits']>52
    assert np.array_equal(op.table(),t)
    assert op.payload['u'] in range(1,10) and op.payload['v'] in range(1,10)


def test_sparse_exception_coordinates_are_minimal(inputs):
    t=inputs['sparse_exception']
    r=infer_new_categories(t)
    op=next(x for x in r['abilities'] if x.family=='sparse_orbit_exceptions')
    assert len(op.payload['exceptions'])==2
    assert op.representation_bits==70
    assert op.certify()['scalar_numpy_agree']
    assert np.array_equal(op.table(),t)


def test_random_control_no_forced_invention(inputs):
    r=infer_new_categories(inputs['unstructured_random'])
    assert r['status']=='no_verified_new_family'
    assert not r['abilities']
    assert r['next_research_task']
    assert r['prediction_advantage']=='not_established'


def test_existing_v31_categories_not_counted_as_new():
    a,b=np.indices((10,10))
    orb=np.array([0,2,1,0,1,2,2,1,0,2],dtype=np.uint8)
    r=infer_new_categories(orb[(a-b)%10])
    assert r['old_best_bits']==44
    assert not r['abilities']
    assert r['status']=='no_verified_new_family'


@pytest.mark.parametrize('kwargs',[{'max_exceptions':-1},{'max_exceptions':7},
                                   {'max_exceptions':1.5},{'min_saved_bits':0},
                                   {'min_saved_bits':1000}])
def test_invalid_search_settings_rejected(inputs,kwargs):
    with pytest.raises(ValueError):infer_new_categories(inputs['affine_modular'],**kwargs)


def test_invalid_table_shape_or_nan_or_bool_rejected():
    for bad in (np.zeros((5,5),int),np.zeros((10,10),float),
                np.ones((10,10),bool),np.full((10,10),4,int)):
        with pytest.raises(ValueError):infer_new_categories(bad)


def test_signature_denies_payload_mutation(inputs):
    op=infer_new_categories(inputs['affine_modular'])['abilities'][0]
    record=json.loads(json.dumps(op.__dict__))
    record['payload']['orbit'][0]=(record['payload']['orbit'][0]+1)%op.levels
    with pytest.raises(ValueError,match='ID'):CategoryHypothesis(**record)
    record['id']='evil'
    with pytest.raises(ValueError):CategoryHypothesis(**record)


def test_refuse_arbitrary_code_and_bad_coordinates(inputs):
    op=infer_new_categories(inputs['sparse_exception'])['abilities'][0]
    bad=dict(op.__dict__)
    bad['family']="__import__('os').system('malicious')"
    with pytest.raises(ValueError):CategoryHypothesis(**bad)
    with pytest.raises(ValueError):op.call(-1,0)
    with pytest.raises(ValueError):op.call(True,2)
    with pytest.raises(ValueError):op.vector(np.array([2,10]),np.array([2,2]))


def test_reproducible_identity_and_cryptographic_hash(inputs):
    a=infer_new_categories(inputs['two_state_piecewise'])['abilities']
    b=infer_new_categories(inputs['two_state_piecewise'])['abilities']
    assert [op.id for op in a]==[op.id for op in b]
    assert all(op.card()['source_table_sha256']==hashlib.sha256(inputs['two_state_piecewise'].tobytes()).hexdigest() for op in a)


def test_registry_append_only_and_integrity(tmp_path,inputs):
    db=HypothesisRegistry(tmp_path/'v32.sqlite')
    op=infer_new_categories(inputs['affine_modular'])['abilities'][0]
    assert db.register(op)
    assert not db.register(op)
    assert db.get(op.id).certify()['checked_pairs']==100
    assert db.summary()[0]['status']=='research_only'
    with sqlite3.connect(db.path) as conn:
        conn.execute('UPDATE v32_hypotheses SET source_sha=? WHERE id=?',('0'*64,op.id))
    with pytest.raises(ValueError):db.get(op.id)


def test_existing_aan_and_esse_interfaces_accept_new_safe_operator(inputs):
    op=infer_new_categories(inputs['two_state_piecewise'])['abilities'][0]
    mask=run_operator_on_100k(op,(0,4),(0,))
    assert len(mask['mask'])==100000
    assert mask['retained']+mask['removed']==100000
    out=compose_abilities({'apply':op.id,'args':[{'digit':0},{'digit':4}]},{op.id:op})
    assert len(out['outputs'])==100000
    for n in [0,12345,95621,99999]:
        assert int(out['outputs'][n])==op.call(n//10000,n%10)


def test_duplicate_provenance_keeps_initial_source(tmp_path,inputs):
    db=HypothesisRegistry(tmp_path/'database.sqlite')
    first=infer_new_categories(inputs['affine_modular'],source_id='first')['abilities'][0]
    second=infer_new_categories(inputs['affine_modular'],source_id='second')['abilities'][0]
    assert first.id==second.id
    assert db.register(first) and not db.register(second)
    assert db.get(first.id).source_id=='first'


def test_tampered_exception_repair_not_accepted(inputs):
    op=next(x for x in infer_new_categories(inputs['sparse_exception'])['abilities']
            if x.family=='sparse_orbit_exceptions')
    bad=json.loads(json.dumps(op.__dict__))
    bad['payload']['exceptions'].append(bad['payload']['exceptions'][0])
    with pytest.raises(ValueError):CategoryHypothesis(**bad)


def test_cli_demo_and_table_mode(tmp_path,inputs):
    backend=Path(__file__).resolve().parents[1]
    report=tmp_path/'report.json';registry=tmp_path/'registry.sqlite'
    for action,more in [('demo',[]),('table',['--table-json',str(tmp_path/'table.json')])]:
        (tmp_path/'table.json').write_text(json.dumps(inputs['two_state_piecewise'].tolist()),encoding='utf-8')
        proc=subprocess.run([sys.executable,'research_v32.py',action,'--report',str(report),
                             '--registry',str(registry),*more],cwd=backend,capture_output=True,text=True,timeout=45)
        assert proc.returncode==0,proc.stderr
        r=json.loads(report.read_text(encoding='utf-8'))
        assert r['created_abilities']>=1
        assert r['esse_research_mask']['total']==100000
        assert r['status']=='research_only'


def test_historical_holdout_never_used_for_invention():
    rng=np.random.default_rng(73)
    draws=[''.join(str(int(d)) for d in row) for row in rng.integers(0,10,(235,5))]
    a=study_historical_operators(draws,maximum=1)
    b=study_historical_operators(draws[:-110]+['99999']*110,maximum=1)
    assert a['training_periods']==125
    assert a['training_history_sha256']==b['training_history_sha256']
    assert a['abilities']==b['abilities']
    assert a['prediction_advantage']=='not_established'
