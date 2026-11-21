"""V3.7.15 end-to-end PL5 rule-pool benchmark acceptance tests."""
import json
from pathlib import Path
from benchmark_ga_cs_v3715 import run_experiment


def test_real_universe_budget_matching_and_zero_false_feasibility():
    outcome = run_experiment(seeds=(1,), evaluations=36, include_infeasible=True)
    assert outcome['domain'] == 100000
    assert outcome['source_rule_pool'] == 'benchmark_high_throughput_v3714._rules'
    assert outcome['rule_count'] == 20
    assert outcome['protocol']['fitness_uses_draw_labels'] is False
    assert len(outcome['scenarios']['feasible']['trials']) == 6
    for trial in outcome['scenarios']['feasible']['trials']:
        assert trial['evaluations'] == 36
        assert trial['survivors'] >= 28672
        assert trial['best_genome'] < (1 << 20)
        assert trial['selected_rule_names']
    assert outcome['scenarios']['infeasible_100']['proven_infeasible'] is True
    assert outcome['scenarios']['infeasible_100']['best_possible_survivors'] == 28672
    assert all(not x['feasible'] for x in outcome['scenarios']['infeasible_100']['trials'])
    assert len(outcome['scenarios']['infeasible_100']['trials']) == 6
    assert all(x['evaluations'] == 36 for x in outcome['scenarios']['infeasible_100']['trials'])


def test_repeated_seed_produces_identical_algorithm_results_except_runtime():
    a = run_experiment(seeds=(7,), evaluations=30, include_infeasible=False)
    b = run_experiment(seeds=(7,), evaluations=30, include_infeasible=False)
    for x,y in zip(a['scenarios']['feasible']['trials'],b['scenarios']['feasible']['trials']):
        for field in ('method','best_genome','survivors','fitness','feasible','selected_rule_names','best_trace'):
            assert x[field] == y[field]
    assert a['scenarios']['feasible']['independent_oracle_mismatches'] == 0


def test_independent_oracle_detects_same_size_but_wrong_ticket_membership():
    """A sample-count-only oracle would silently miss this wrong bitmap."""
    import pytest
    from pailie5.basic_filters import BasicConstraint
    from pailie5.high_throughput_v3714 import ExactFilterEngine
    from pailie5.ga_cs_optimizer_v3715 import SearchProblem
    from benchmark_ga_cs_v3715 import _trial
    rule = BasicConstraint('digit_1',minimum=5)
    engine = ExactFilterEngine()
    engine.add_basic('r',rule)
    correct = engine._compile('r')
    wrong = correct ^ 1 ^ (1 << 90000)
    assert correct.bit_count() == wrong.bit_count()
    p=SearchProblem(masks=(wrong,),rule_names=('r',),universe_size=100000,
                    target=50000,min_survivors=49000,max_survivors=51000,min_active=1)
    with pytest.raises(AssertionError,match='membership'):
        _trial('random',p,[('r',rule)],seed=2,evaluations=1)
