"""Adversarial review checks added without changing the frozen benchmark code."""
from dataclasses import replace
from pailie5.ablation_search_v373 import AblationConfig,Mechanisms,fit_budgeted
from pailie5.structure_search_v372 import CellDataset


def data():
    return CellDataset(tuple((a,b,(a*b+a)%10) for a in range(6) for b in range(10)))


def test_all_enabled_generators_are_actually_exercised():
    r=fit_budgeted(data(),AblationConfig(evaluation_budget=900))
    assert all(r.proposal_counts.get(k,0)>0 for k in ('mutation','crossover','guided','random_grammar'))


def test_grammar_only_never_uses_elite_adaptive_generators():
    r=fit_budgeted(data(),AblationConfig(evaluation_budget=900),
                   Mechanisms(mutation=False,crossover=False,guided=False,warm_start=False))
    assert r.proposal_counts.get('random_grammar',0)>0
    assert all(r.proposal_counts.get(k,0)==0 for k in ('mutation','crossover','guided','warm_start'))


def test_evaluation_and_proposal_counter_conservation():
    r=fit_budgeted(data(),AblationConfig(evaluation_budget=900))
    assert sum(r.proposal_counts.values())==r.proposals
    assert sum(r.evaluation_counts.values())==r.evaluations==900
    assert r.proposals==r.evaluations+r.rejected_counts.get('bounds_or_shape',0)+r.rejected_counts.get('duplicate_AST',0)


def test_proposal_guard_never_claims_full_matched_budget():
    r=fit_budgeted(data(),AblationConfig(evaluation_budget=80,proposal_factor=1))
    assert r.proposals<=80
    assert r.evaluations<80 and not r.budget_matched


def test_training_row_order_cannot_change_fit():
    d=data()
    shuffled=CellDataset(tuple(reversed(d.rows)))
    cfg=AblationConfig(evaluation_budget=350)
    assert fit_budgeted(d,cfg).to_dict()==fit_budgeted(shuffled,cfg).to_dict()
