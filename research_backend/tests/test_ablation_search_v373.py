import importlib
from dataclasses import replace
import numpy as np
import pytest
from pailie5.structure_search_v372 import CellDataset
from pailie5.structure_evidence_v372 import evaluate_frozen

def m():
    return importlib.import_module('pailie5.ablation_search_v373')

def training():
    return CellDataset(tuple((a,b,(a+b)%10) for a in range(6) for b in range(10)))

def test_ablation_module_exists():
    assert importlib.util.find_spec('pailie5.ablation_search_v373') is not None

def test_exact_budget_even_after_exact_training_fit():
    r=m().fit_budgeted(training(),m().AblationConfig(evaluation_budget=100))
    assert r.training_errors == 0
    assert r.evaluations == 100 and r.budget_matched
    assert r.first_exact_evaluation <= 100

def test_reproducible_training_only_fit():
    cfg=m().AblationConfig(evaluation_budget=200, seed=84)
    a,b=m().fit_budgeted(training(),cfg),m().fit_budgeted(training(),cfg)
    assert a.to_dict()==b.to_dict()
    frozen=a.to_dict()
    held=CellDataset(tuple((x,y,(x+y)%10) for x in range(6,10) for y in range(10)))
    shifted=CellDataset(tuple((x,y,(z+1)%10) for x,y,z in held.rows))
    assert evaluate_frozen(a.operator,held)['errors']==0
    assert evaluate_frozen(a.operator,shifted)['errors']==40
    assert a.to_dict()==frozen

@pytest.mark.parametrize('disabled',['mutation','crossover','guided'])
def test_disabled_generator_is_never_used(disabled):
    mech=replace(m().Mechanisms(),**{disabled:False})
    r=m().fit_budgeted(training(),m().AblationConfig(evaluation_budget=800),mech)
    assert r.proposal_counts.get(disabled,0)==0
    assert r.evaluations==800 and r.budget_matched
    assert r.proposal_counts.get('random_grammar',0)>0

def test_complexity_off_has_no_size_tiebreak():
    assert m().rank_key(1,3,'z',0.0) > m().rank_key(1,11,'a',0.0)
    assert m().rank_key(1,3,'z',0.05) < m().rank_key(1,11,'a',0.05)

def test_warm_starts_charged_and_can_be_disabled():
    warm=(('binary','add',('a',),('b',)),)
    cfg=m().AblationConfig(evaluation_budget=2)
    yes=m().fit_budgeted(training(),cfg,warm_starts=warm)
    no=m().fit_budgeted(training(),cfg,replace(m().Mechanisms(),warm_start=False),warm_starts=warm)
    assert yes.evaluations==no.evaluations==2
    assert yes.training_errors==0
    assert yes.evaluation_counts.get('warm_start')==1
    assert no.proposal_counts.get('warm_start',0)==0

def test_tiny_budget_preserves_safe_fallback():
    r=m().fit_budgeted(training(),m().AblationConfig(evaluation_budget=1))
    assert r.evaluations==1 and r.operator.expression==('a',)
    assert r.operator.to_dict()['production_enabled'] is False

@pytest.mark.parametrize('kwargs',[{'evaluation_budget':0},{'evaluation_budget':True},
    {'seed':-1},{'max_nodes':17},{'max_depth':9},{'pool_size':1},
    {'bootstrap_fraction':float('nan')},{'complexity_weight':float('inf')},
    {'proposal_factor':0},{'batch_size':0}])
def test_invalid_config_rejected(kwargs):
    with pytest.raises(ValueError): m().AblationConfig(**kwargs)

def test_non_boolean_mechanism_rejected():
    with pytest.raises(ValueError): m().Mechanisms(mutation=1)

def test_reject_untrusted_warm_start():
    with pytest.raises(ValueError):
        m().fit_budgeted(training(),warm_starts=(('eval','os.remove'),))
