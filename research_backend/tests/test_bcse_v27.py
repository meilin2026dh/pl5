"""V2.7 BCSE: finite model posterior, evidence locks, null and biased controls."""
import math
import numpy as np
import pytest
from pailie5.bcse_v27 import (Constraint, constraints_from_json, constraint_masks,
    group_redundancy, positional_baseline, validate_history, study, full_ranking,
    DEFAULT_CONSTRAINTS, models_for, _energies, evaluate, WARMUP)


def random_draws(seed=9,n=165):
    return [f'{i:05d}' for i in np.random.default_rng(seed).integers(100000,size=n)]


def test_cards_and_contract():
    cards=[c.card() for c in DEFAULT_CONSTRAINTS]
    assert len(cards)==6
    assert len(set(c['id'] for c in cards))==6
    assert all('history_prefix_before_target' in c['inputs'] for c in cards)
    assert all(c['permission']=='research_only' for c in cards)
    assert constraints_from_json([{'id':'x','kind':'step_large','threshold':8}])[0].threshold==8


@pytest.mark.parametrize('rows',[[{'id':'x','kind':'evil'}],[{'id':'x','kind':'step_large','threshold':0}],
                                   [{'id':'x','kind':'parity_extreme','threshold':8}],
                                   [{'id':'x','kind':'parity_extreme'},{'id':'x','kind':'step_large'}],
                                   [{'id':'x','kind':'step_large','inject':'x'}]])
def test_reject_invalid_constraints(rows):
    with pytest.raises((ValueError,TypeError)):constraints_from_json(rows)


def test_mask_examples_and_only_history_prefix():
    p=np.array([10234,12345,23456])
    masks=constraint_masks(p)
    assert masks.shape==(6,100000)
    # 01234 contains adjacent 1 only, so no large jump
    assert not masks[0,1234]
    assert masks[0,90909]
    assert masks[2,11111] and not masks[2,12345]
    # arithmetic sums 10,15,20 -> 25
    assert masks[4,34567]
    assert not masks[4,12345]
    assert np.array_equal(masks,constraint_masks(p))
    # exact date t is not used in past mask
    extra=np.r_[p,99999]
    assert np.array_equal(masks,constraint_masks(extra[:-1]))


def test_redundancy_deduplicates_identical_rules():
    a=Constraint('s1','step_large',7)
    b=Constraint('s2','step_large',7)
    masks=constraint_masks(np.array([12345,12345,12345]),(a,b))
    dup=group_redundancy(masks,(a,b))
    assert dup==[{'id':'s2','against':'s1','phi':pytest.approx(1.)}]
    models,priors=models_for((a,b),dup)
    assert all('s2' not in name for name,base,weights,_ in models)
    assert sum(priors)==pytest.approx(1.)


def test_dirichlet_baseline_is_normalized_and_unbiased_under_symmetric_counts():
    d=np.array([int(f'{i:05d}') for i in range(100000)],dtype=np.int32)
    p=positional_baseline(d)
    assert p.shape==(100000,) and p.sum()==pytest.approx(1.)
    assert p.min()==pytest.approx(1/100000)


def test_iid_fallback_and_pmf_and_credible_intervals():
    h=random_draws(n=165)
    r=study(h,seed=7,test_periods=25,validation_periods=25,budget=20)
    assert r['status']=='research_only'
    assert r['mode'] in ('uniform_fallback','validated_model')
    assert r['holdout']['periods']==25
    assert r['fair_hit_probability']==pytest.approx(20/100000)
    assert len(r['experimental_top_k'])==20 and len(set(r['experimental_top_k']))==20
    assert len(r['equal_budget_random_control'])==20
    order,p=full_ranking(h,r)
    assert order.shape==(100000,) and set(order.tolist())==set(range(100000))
    assert p.sum()==pytest.approx(1.,abs=1e-10)
    assert [f'{int(v):05d}' for v in order[:20]]==r['experimental_top_k']
    for x in r['candidate_details']:
        lo,hi=x['model_probability_95pct_credible_interval']
        assert lo<=hi and 0<=x['model_probability_mean']<=1
        assert x['penalty_95pct_credible_interval'][0]<=x['penalty_95pct_credible_interval'][1]
        assert 0<=x['posterior_mass_models_below_uniform']<=1
    assert abs(sum(r['posterior_model_weights_training'].values())-1)<1e-10


def test_no_holdout_tuning_or_leakage():
    h=random_draws(seed=22,n=160)
    altered=h[:-25]+['00000']*25
    a=study(h,test_periods=25,validation_periods=25,budget=10)
    b=study(altered,test_periods=25,validation_periods=25,budget=10)
    assert a['posterior_model_weights_training']==b['posterior_model_weights_training']
    assert a['validation']==b['validation']
    assert a['gate']==b['gate']


def test_random_control_precommitted_and_deterministic():
    h=random_draws(seed=17,n=155)
    a=study(h,test_periods=20,validation_periods=20,seed=94,budget=8)
    b=study(h,test_periods=20,validation_periods=20,seed=94,budget=8)
    assert a==b


def test_report_rejects_wrong_history_and_constraints():
    h=random_draws(seed=17,n=155)
    a=study(h,test_periods=20,validation_periods=20,budget=8)
    other=h.copy();other[0]='99999'
    with pytest.raises(ValueError):full_ranking(other,a)
    with pytest.raises(ValueError):full_ranking(h,a,[{'id':'other','kind':'parity_extreme'}])


def test_nonuniform_fixture_can_create_an_advantage_on_heldout():
    # Controlled synthetic process deliberately excludes large steps; this is NOT official data.
    rng=np.random.default_rng(111)
    universe=np.arange(100000)
    from pailie5.engine import DIGITS
    subset=universe[(np.abs(np.diff(DIGITS.astype(int),axis=1))<7).all(axis=1)]
    h=[f'{i:05d}' for i in rng.choice(subset,size=320,replace=True)]
    r=study(h,test_periods=40,validation_periods=40,budget=20,
            constraints=[{'id':'step','kind':'step_large','threshold':7}],seed=55)
    assert r['mode']=='validated_model'
    assert r['holdout']['mean_log_gain']>0
    assert r['posterior_model_weights_training']['uniform']<.5


def test_null_replays_are_explicitly_synthetic():
    h=random_draws(seed=28,n=155)
    r=study(h,seed=3,test_periods=20,validation_periods=20,budget=8,null_trials=1)
    assert len(r['iid_null_simulations'])==1
    assert r['prediction_warning']


def test_source_validation():
    with pytest.raises(ValueError):validate_history(['00000']*149)
    with pytest.raises(ValueError):validate_history(['１２３４５']*170)
    with pytest.raises(ValueError):study(random_draws(n=155),budget=101)
    with pytest.raises(ValueError):study(random_draws(n=155),test_periods=200)


def test_signature_model_normalization():
    m,priors=models_for(DEFAULT_CONSTRAINTS,[])
    energy,expo,flags=_energies(m,len(DEFAULT_CONSTRAINTS))
    assert energy.shape==(len(m),64)
    assert expo.shape==energy.shape
    assert np.isfinite(expo).all()
    assert priors.sum()==pytest.approx(1.)
    assert (energy[0]==0).all() and (expo[0]==1).all()


def test_full_100k_diagnostics_and_mismatch_guard():
    from pailie5.bcse_v27 import full_diagnostics
    h=random_draws(seed=4,n=155)
    result=study(h,budget=10,test_periods=20,validation_periods=20,seed=19)
    ordered,vec=full_diagnostics(h,result)
    assert len(ordered)==100000 and len(set(ordered))==100000
    assert set(vec)=={'model_probability_mean','model_probability_ci_low',
                     'model_probability_ci_high','penalty_mean','penalty_ci_low',
                     'penalty_ci_high','posterior_mass_below_uniform','signature'}
    assert vec['model_probability_mean'].sum()==pytest.approx(1.,abs=1e-10)
    assert (vec['model_probability_ci_low']<=vec['model_probability_ci_high']).all()
    assert (vec['penalty_ci_low']<=vec['penalty_ci_high']).all()
    assert vec['signature'].max()<64
    assert [f'{int(n):05d}' for n in ordered[:10]]==result['experimental_top_k']
