import json
import sqlite3
import numpy as np
import pytest
from pailie5.autolift_v28 import (
    Lift, invent, validate_expr, calc_expr, scalar_codes, unique_lifts,
    validated_history, fit_lift, distill, pmf, crosscheck_full, study, register,
)
from pailie5.engine import DIGITS


def iid(n=170,seed=11):
    return [f'{int(i):05d}' for i in np.random.default_rng(seed).integers(100000,size=n)]


def bias(n=440,seed=15):
    r=np.random.default_rng(seed).integers(0,10,size=(n,5))
    r[:,1]=r[:,0]
    return [''.join(map(str,row)) for row in r]


def test_invent_deterministic_and_bounded():
    a=invent(42,18)
    assert [x.id for x in a]==[x.id for x in invent(42,18)]
    assert len({x.id for x in a})==18
    assert all(4<=x.bins<=121 for x in a)

@pytest.mark.parametrize('expr',[{'op':'__import__','value':'os'},
                                {'op':'digit','pos':5},
                                {'op':'lag','pos':0,'back':0},
                                {'op':'sum','extra':'x'},
                                {'op':'add','left':{'op':'sum'},'right':{'op':'open'}}])
def test_rejects_unsafe_expression(expr):
    with pytest.raises(ValueError):validate_expr(expr)


def test_rejects_invalid_dimensions():
    with pytest.raises(ValueError):Lift({'op':'sum'},{'op':'sum'},0,8)


def test_no_future_data_in_codes():
    s=invent(55,9)[5]
    arr=validated_history(iid(170))
    a=s.codes(arr[:70])
    assert a.shape==(100000,)
    # Entire history changes the lag context, but fixed 70-period *prefix* does not.
    swapped=arr.copy();swapped[100:]=0
    assert np.array_equal(s.codes(arr[:70]),s.codes(swapped[:70]))


def test_scalar_vector_full_domain():
    s=invent(98,7)[6]
    hist=validated_history(iid())
    assert crosscheck_full(s,hist)['checked']==100000


def test_feature_map_and_probability_normalization():
    arr=validated_history(iid())
    s=invent(42,4)[0]
    f=fit_lift(s,arr,110)
    assert f['observed'].sum()==107
    assert abs(f['expected'].sum()-107)<1e-6
    assert (np.abs(f['sparse_logratio'])>0).sum()<=4
    p=pmf(s,f,arr)
    assert np.all(p>0) and abs(p.sum()-1)<1e-12
    assert len(distill(s,f))<=4


def test_relabel_equivalent_partition_is_deduplicated():
    x=Lift({'op':'digit','pos':0},{'op':'digit','pos':1},10,10)
    y=Lift({'op':'digit','pos':1},{'op':'digit','pos':0},10,10)
    keep,dups=unique_lifts([x,y],validated_history(iid()))
    assert len(keep)==1 and len(dups)==1


def test_iid_picks_and_caution():
    r=study(iid(180,24),maximum=4,seed=47,budget=17,validation_periods=30,test_periods=25)
    assert r['fair_independent_hit_probability']==17/100000
    assert len(r['experimental_top_k'])==17
    assert len(set(r['experimental_top_k']))==17
    assert len(r['equal_budget_random_control'])==17
    assert r['independent_operator_crosscheck']['pass']
    assert r['algorithm_promotion'].startswith('FORBIDDEN')
    assert r['gate']['passed'] is False


def test_biased_training_is_explorable_without_claim():
    r=study(bias(300),maximum=4,budget=13,validation_periods=55,test_periods=45)
    assert r['unique']>=3 and len(r['experiments'])>=3
    assert any(x['validation']['mean_log_gain']>0 for x in r['experiments'])
    assert r['holdout']['periods']==45
    assert 'prediction_advantage' in r['operator_cards'][0]


def test_append_only_registry(tmp_path):
    r=study(iid(170,29),maximum=3,budget=10,validation_periods=25,test_periods=25)
    db=tmp_path/'r.sqlite'
    assert register(r,db)==r['unique']
    assert register(r,db)==0
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT COUNT(*) FROM v28_runs').fetchone()[0]==1
        assert {row[0] for row in con.execute('SELECT DISTINCT status FROM v28_algorithms')}=={'research_only'}


def test_bad_history_blocked():
    with pytest.raises(ValueError):study(['12a45']*170)
    with pytest.raises(ValueError):study(iid(149))
    with pytest.raises(ValueError):study(iid(170),maximum=25)


def test_mask_convention_zero_prefix():
    s=invent(2026,4)[0]
    arr=validated_history(iid())
    x=s.codes(arr,np.array([0,9,10,99999]))
    assert x[0]==0 and all(0<=int(v)<s.bins for v in x)


def test_training_is_invariant_to_holdout_edits():
    arr=validated_history(iid(180))
    s=invent(67,4)[0]
    f1=fit_lift(s,arr,125)
    altered=arr.copy();altered[151:]=77777
    f2=fit_lift(s,altered,125)
    assert np.array_equal(f1['sparse_logratio'],f2['sparse_logratio'])
