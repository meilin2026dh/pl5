"""HDSE tests: mathematics, no-leakage, safety, and deterministic experiments."""
import math
import numpy as np
import pytest
from pailie5.highdim_v26 import (LiftSpec, proposals, fit, study, eval_rows,
                                 history_ids, capabilities, _splits)


def make_draws(seed=56,n=210):
    return [f'{x:05d}' for x in np.random.default_rng(seed).integers(100000,size=n)]


def test_capability_coordinates_and_hypotheses():
    cards=capabilities()
    assert {x['spec']['family'] for x in cards}=={'tensor','temporal','spectral'}
    assert next(x for x in cards if x['spec']['family']=='tensor' and x['spec']['order']==3)['declared_feature_coordinates']==11050
    assert next(x for x in cards if x['spec']['family']=='temporal' and x['spec']['order']==2)['declared_feature_coordinates']==5550
    assert next(x for x in cards if x['spec']['family']=='spectral' and x['spec']['order']==3)['declared_feature_coordinates']==8145
    assert len(proposals(17,5))==5 and proposals(17,5)==proposals(17,5)
    assert len({x.id for x in proposals(17,12)})==12
    assert all(x['prediction_advantage']=='unverified' for x in cards)


@pytest.mark.parametrize('invalid', [
    {'family':'arbitrary'}, {'family':'temporal','order':3},
    {'family':'tensor','order':0}, {'family':'spectral','harmonics':0},
    {'family':'tensor','alpha':1},
])
def test_reject_invalid_hypothesis(invalid):
    with pytest.raises(ValueError):LiftSpec(**invalid)


def test_full_pmf_normalization_and_nonnegative():
    train=history_ids(make_draws())[:150]
    for spec in [LiftSpec('tensor',1),LiftSpec('tensor',2),LiftSpec('tensor',3),
                 LiftSpec('temporal',1),LiftSpec('temporal',2),
                 LiftSpec('spectral',1),LiftSpec('spectral',2),LiftSpec('spectral',3)]:
        m=fit(spec,train)
        p=m.all_values(int(train[-1]),int(train[-2]))
        assert p.shape==(100000,) and np.all(p>=0) and np.isfinite(p).all()
        assert float(p.sum())==pytest.approx(1.,abs=1e-10)
        selected=np.array([0,12,12345,99999],dtype=np.int32)
        assert m.values(selected,int(train[-1]),int(train[-2]))==pytest.approx(p[selected])


def test_bounded_history_and_digits():
    with pytest.raises(ValueError):history_ids(['1234']*140)
    with pytest.raises(ValueError):history_ids(['１２３４５']*140)
    with pytest.raises(ValueError):history_ids(make_draws()[:40])
    with pytest.raises(ValueError):_splits(125,30)
    assert history_ids(['00000']*120)[0]==0


def test_holdout_is_never_used_for_selection():
    base=make_draws(23,180)
    a=study(base,seed=7,maximum=4,test_periods=30,budget=15)
    modified=base[:-30]+['00000']*30
    b=study(modified,seed=7,maximum=4,test_periods=30,budget=15)
    assert a['hypotheses']==b['hypotheses']
    assert a['uniform_fallback']==b['uniform_fallback']
    assert a['lambda']==b['lambda']
    assert a['selected']==b['selected']
    assert a['splits']==b['splits']


def test_determinism_and_budget():
    history=make_draws(34,160)
    a=study(history,seed=10,maximum=4,test_periods=30,budget=22)
    b=study(history,seed=10,maximum=4,test_periods=30,budget=22)
    assert a==b
    assert len(a['experimental_top_k'])==22
    assert len(set(a['experimental_top_k']))==22
    assert len(a['equal_budget_random_control'])==22
    assert a['fair_probability_exact']==pytest.approx(0.00022)
    assert a['baseline_log_loss']==pytest.approx(math.log(100000))
    assert a['status']=='research_only'


def test_full_null_selection_repeated():
    r=study(make_draws(36,160),seed=3,maximum=3,test_periods=25,budget=7,null_trials=1)
    assert r['null_controls']['simulations']==1
    assert r['null_controls']['full_selection_repeated'] is True
    assert len(r['null_controls']['holdout_gain'])==1


def test_informative_temporal_synthetic_fixture():
    # Controlled predictable sequence can be learned; this says nothing about lotteries.
    seq=[f'{(17 if i%2 else 42):05d}' for i in range(210)]
    history=history_ids(seq)
    m=fit(LiftSpec('temporal',2,alpha=25),history[:120])
    assert m.values(history[120:121],int(history[119]),int(history[118]))[0]>1/100000
    assert eval_rows(m,history,120,160,1)['mean_log_gain']>0


def test_models_do_not_expose_execution_interface():
    m=fit(LiftSpec('spectral',3), history_ids(make_draws())[:180])
    assert 1<=len(m.peaks)<=8
    assert all(len(p['frequency'])==5 and all(0<=x<=9 for x in p['frequency']) for p in m.peaks)
    assert all(p['amplitude']>=0 for p in m.peaks)


def test_full_rank_export_matches_topk():
    from pailie5.highdim_v26 import full_ranking
    data=make_draws(11,160)
    result=study(data,seed=2,maximum=3,test_periods=30,budget=15)
    order,p=full_ranking(data,result)
    assert len(order)==100000 and len(set(order))==100000
    assert p.sum()==pytest.approx(1.)
    assert [f'{x:05d}' for x in order[:15]]==result['experimental_top_k']


def test_full_ranking_rejects_wrong_history():
    from pailie5.highdim_v26 import full_ranking
    data=make_draws(3,160)
    r=study(data,maximum=3,test_periods=30)
    altered=list(data);altered[2]='99999' if altered[2]!='99999' else '11111'
    with pytest.raises(ValueError):full_ranking(altered,r)
