import hashlib
from dataclasses import asdict
import numpy as np
import pytest
from pailie5.representation_v25 import (Representation, propose, audit, vector,
    study, _distribution, _frozen_gain, baseline_profiles)

DATA=[f'{(i*7919+17*i*i)%100000:05d}' for i in range(135)]


def test_determinism_and_bounded_proposals():
    a=propose(1,16)
    b=propose(1,16)
    assert a==b
    assert len({x.id for x in a})==16
    assert all(vector(x).shape==(100000,) for x in a)
    assert all(not vector(x).flags.writeable for x in a)


def test_invalid_specs_rejected():
    with pytest.raises(ValueError):Representation('import os')
    with pytest.raises(ValueError):Representation('weighted_mod',positions=(0,0))
    with pytest.raises(ValueError):Representation('weighted_mod',modulus=1)
    with pytest.raises(ValueError):Representation('affine_relabel',weights=(2,1))
    with pytest.raises(ValueError):Representation('pair_sum_mod',positions=(0,1,2),weights=(1,1,1))
    with pytest.raises(ValueError):propose(42,61)


def test_computed_features_hand_checked():
    assert vector(Representation('signed_difference',positions=(0,4)))[12345]==-4
    assert vector(Representation('pair_sum_mod',positions=(0,4),modulus=7,offset=0))[12345]==(1+5)%7
    assert vector(Representation('cross_term_mod',positions=(0,1,2),weights=(1,1,1),modulus=11))[12345]==(1*2+3)%11
    assert vector(Representation('weighted_mod',positions=(0,1,4),weights=(2,-3,1),modulus=13))[12345]==(2*1-3*2+5)%13


def test_partition_fingerprint_relabel_invariance_and_difference():
    a=np.tile(np.array([0,0,1,2],dtype=np.int64),25000)
    b=np.tile(np.array([9,9,7,3],dtype=np.int64),25000)
    c=np.tile(np.array([9,7,9,3],dtype=np.int64),25000)
    assert _distribution(a)[3]==_distribution(b)[3]
    assert _distribution(a)[3]!=_distribution(c)[3]


def test_bijection_tagged_no_predictive_promotion():
    v=Representation('affine_relabel',weights=(3,1))
    assert len(np.unique(vector(v)))==100000
    report=audit([v])
    assert report['reviewed'][0]['status']=='invertible_relabel_only'
    assert report['accepted']==0
    assert report['reviewed'][0]['capability']['predictive_advantage']=='unverified'


def test_identical_partition_dedup():
    a=Representation('pair_sum_mod',positions=(0,1),modulus=7,weights=(1,1))
    b=Representation('weighted_mod',positions=(0,1),weights=(1,1),modulus=7)
    x=audit([a,b])
    assert x['accepted']==1
    assert x['reviewed'][1]['status']=='redundant_partition'
    assert x['reviewed'][1]['equivalent_to']==a.id


def test_formal_baselines_present():
    assert len(baseline_profiles())>=9
    assert all(len(signature)==64 for _,signature in baseline_profiles())


def test_study_time_split_and_model_loss():
    r=study(DATA,count=12,test_periods=25,seed=11)
    assert r['splits']['development_train']+r['splits']['development_validation']+25==len(DATA)
    assert r['historical_holdout']['periods']==25
    assert r['status']=='research_only'
    assert len(r['next_draw_exploratory_top100'])==len(set(r['next_draw_exploratory_top100']))==100
    assert len(r['next_draw_random_control_100'])==100
    assert r['next_draw_fair_coverage']==.001
    assert np.isfinite(r['historical_holdout']['avg_log_gain_nats'])


def test_holdout_changes_do_not_select_different_winner():
    a=study(DATA,test_periods=25,count=10,seed=100)
    b=study(DATA[:-25]+['00000']*25,test_periods=25,count=10,seed=100)
    assert a['selected_capability']['id']==b['selected_capability']['id']
    assert a['development_leaderboard']==b['development_leaderboard']
    assert a['historical_holdout']!=b['historical_holdout']


def test_all_equal_history_is_finite():
    r=study(['12345']*105,test_periods=30,count=10,seed=10)
    assert np.isfinite(r['historical_holdout']['avg_log_gain_nats'])
    assert 0<min(r['next_draw_model_probabilities'])<1


def test_null_probability_and_normalization():
    s=Representation('weighted_mod', positions=(0,1),weights=(3,2),modulus=7)
    data=vector(s)
    val,inv,sizes=np.unique(data,return_inverse=True,return_counts=True)
    counts=np.bincount(inv[[int(x) for x in DATA]],minlength=len(sizes))
    mass=(counts+100*sizes/100000)/(len(DATA)+100)
    probs=(mass/sizes)[inv]
    assert probs.sum()==pytest.approx(1.,abs=1e-10)
    assert _frozen_gain(s,DATA[:80],DATA[80:])['null_avg_log_loss_nats']==pytest.approx(np.log(100000))


def test_history_validation_and_no_external_code():
    with pytest.raises(ValueError):study(['0012']*100,count=5,test_periods=25)
    with pytest.raises(ValueError):study(DATA,count=5,test_periods=8)
    with pytest.raises(ValueError):audit(propose(3,3),max_keep=0)


def test_persistent_cycles_do_not_auto_promote(tmp_path):
    from pailie5.representation_registry_v25 import cycle, status
    db=tmp_path/'repr.db'
    a=cycle(db,count=8,base_seed=100)
    b=cycle(db,count=8,base_seed=100)
    assert a['total_cycles']==1 and b['total_cycles']==2
    assert a['newly_registered']<=a['engineering_candidate_this_cycle']
    assert b['registered_total']>=a['registered_total']
    assert b['seed']!=a['seed']
    assert status(db)['cycles']==2
    assert status(db)['auto_promotion'] is False
    assert status(tmp_path/'notexists.db')['status']=='not_initialized'
