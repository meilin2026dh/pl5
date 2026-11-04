"""V3.4 real parameter adapters, chronology, adversarial input, audit."""
import sqlite3
import numpy as np
import pytest
from pailie5.parameter_hub_v34 import (inventory,fit_step_constraint,fit_lift_moduli,ParameterAudit)

def random_draws(seed=42,n=400):return np.random.default_rng(seed).integers(0,100_000,size=n).tolist()

def test_inventory_honest_and_concrete():
    out=inventory()
    assert out['counts']['trained_v34']==4
    assert out['counts']['search_only']>=3
    assert len({(p['component'],p['name']) for p in out['parameters']})==len(out['parameters'])
    assert out['claim'].startswith('NOT ALL')

def test_step_valid_normalized_and_fallback():
    out=fit_step_constraint(random_draws())
    assert 1<=out['selected_threshold']<=9
    assert len(out['threshold_candidates'])==9
    assert out['split']['sealed_test'][1]==400
    assert out['gate'] in ('uniform_fallback','research_pass')
    assert out['predictive_advantage']=='NOT_ESTABLISHED'
    assert all(np.isfinite(r['weight']) for r in out['threshold_candidates'])

def test_step_test_does_not_change_learned_threshold():
    draws=random_draws(seed=23,n=400)
    first=fit_step_constraint(draws)
    modified=draws.copy();modified[320:]=[99999]*80
    second=fit_step_constraint(modified)
    assert first['selected_threshold']==second['selected_threshold']
    assert first['learned_weight']==second['learned_weight']
    assert first['dev']==second['dev']
    assert first['sealed_test_research_only']!=second['sealed_test_research_only']

def test_lift_static_mod_learning():
    first={'op':'digit','pos':0};second={'op':'digit','pos':1}
    out=fit_lift_moduli(random_draws(),first,second,mod_min=2,mod_max=5)
    assert len(out['trials'])==16
    assert 2<=out['selected']['mod_first']<=5
    assert 2<=out['selected']['mod_second']<=5
    assert out['status'] in ('uniform_fallback','research_pass')
    assert np.isfinite(out['sealed_test_research_only']['mean_nats'])

def test_lift_sealed_future_cannot_change_selection():
    draws=random_draws(seed=61)
    a=fit_lift_moduli(draws,{'op':'digit','pos':0},{'op':'digit','pos':1},mod_max=4)
    altered=draws.copy();altered[320:]=[88888]*80
    b=fit_lift_moduli(altered,{'op':'digit','pos':0},{'op':'digit','pos':1},mod_max=4)
    assert a['selected']==b['selected']
    assert a['selected_dev']==b['selected_dev']
    assert a['sealed_test_research_only']!=b['sealed_test_research_only']

def test_lag_rejected_without_chronological_fit():
    with pytest.raises(ValueError,match='动态lag'):
        fit_lift_moduli(random_draws(),{'op':'lag','pos':0,'back':1},{'op':'digit','pos':2})

@pytest.mark.parametrize('bad',[[],['1']*200,[100000]*200,[-1]*200,[True]*200, list(range(50))])
def test_bad_history_rejected(bad):
    with pytest.raises(ValueError):fit_step_constraint(bad)

def test_invalid_moduli_rejected():
    with pytest.raises(ValueError):fit_lift_moduli(random_draws(),{'op':'digit','pos':0},{'op':'digit','pos':1},mod_min=3,mod_max=14)

def test_parameter_audit_is_append_only_and_verified(tmp_path):
    a=ParameterAudit(tmp_path/'run.sqlite')
    r=fit_step_constraint(random_draws(n=200))
    ident,created=a.register('fit_step',r)
    assert created
    assert a.register('fit_step',r)==(ident,False)
    assert a.read(ident)['data']==r
    assert len(a.summary())==1
    with sqlite3.connect(a.path) as db:db.execute("UPDATE param_runs_v34 SET record='{}' WHERE run_id=?",(ident,))
    with pytest.raises(ValueError,match='altered'):a.read(ident)

def test_synthetic_biased_signal_is_detectable_without_implying_lottery():
    rng=np.random.default_rng(17)
    n=800
    draws=rng.integers(0,100000,size=n)
    # Deviating digit-0: strong genuine synthetic bias.
    draws=(draws%10000)+10000*rng.choice(10,size=n,p=[.55]+[.45/9]*9)
    out=fit_lift_moduli(draws.tolist(),{'op':'digit','pos':0},{'op':'digit','pos':1},mod_min=2,mod_max=10)
    assert out['selected_dev']['mean_nats']>0
    assert out['sealed_test_research_only']['mean_nats']>0
    assert out['predictive_advantage']=='NOT_ESTABLISHED'
