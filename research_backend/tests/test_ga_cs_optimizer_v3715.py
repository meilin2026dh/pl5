"""Acceptance and falsification tests, written before the implementation."""
import pytest
from pailie5.ga_cs_optimizer_v3715 import SearchProblem, optimize, evaluate_genome


def fixture_problem():
    # Five positions, 10 levels; disjoint halfspace masks on a small domain.
    full = (1 << 100) - 1
    masks = tuple(sum(1 << x for x in range(100) if ((x // (i + 2)) % 2)) for i in range(6))
    return SearchProblem(masks=masks, rule_names=tuple(f'r{i}' for i in range(6)),
                         universe_size=100, target=18, min_survivors=3,
                         max_survivors=36, min_active=1, hard_mask=full)


def test_fitness_exact_intersection_and_constraints():
    p = fixture_problem()
    v = evaluate_genome(p, 0)
    assert v.survivors == 100
    assert not v.feasible
    x = evaluate_genome(p, 1)
    assert x.survivors == p.masks[0].bit_count()
    assert not x.feasible  # exceeds max bound 36
    y = evaluate_genome(p, 3)
    assert y.survivors == (p.masks[0] & p.masks[1]).bit_count()
    assert y.rule_count == 2
    with pytest.raises(ValueError): evaluate_genome(p, -1)
    with pytest.raises(ValueError): evaluate_genome(p, 1 << 7)


@pytest.mark.parametrize('method', ['random', 'ga', 'cs', 'ga_cs', 'anneal', 'greedy'])
def test_equal_evaluation_budget_and_trace(method):
    p = fixture_problem()
    r = optimize(p, method=method, evaluations=80, seed=42, switch_ratio=0.3)
    assert r.evaluations == 80
    assert len(r.best_trace) == 80
    assert r.best_trace == tuple(sorted(r.best_trace))
    assert r.best.feasible
    assert r.best == evaluate_genome(p, r.best.genome)
    assert r.best.rule_count >= 1
    assert 0 <= r.best.genome < (1 << len(p.masks))
    assert r.stage_evaluations['ga'] + r.stage_evaluations['cs'] == 80 if method == 'ga_cs' else True


def test_seed_replay_and_no_global_rng_leakage():
    p = fixture_problem()
    a = optimize(p, method='ga_cs', evaluations=90, seed=7)
    b = optimize(p, method='ga_cs', evaluations=90, seed=7)
    assert a.best == b.best
    assert a.best_trace == b.best_trace
    assert a.stage_evaluations == b.stage_evaluations


def test_infeasibility_is_reported_not_claimed_feasible():
    p = SearchProblem(masks=(0b1111, 0b1111), rule_names=('a', 'b'),
                      universe_size=4, target=1, min_survivors=1,
                      max_survivors=1, min_active=1)
    r = optimize(p, method='ga_cs', evaluations=25, seed=0)
    assert not r.best.feasible
    assert r.best.survivors == 4


def test_hard_mask_cannot_be_disabled():
    p = SearchProblem(masks=(0b11111111,0b00001111),rule_names=('soft','restrict'),
                      universe_size=8, hard_mask=0b11001100, target=2,
                      min_survivors=1, max_survivors=4, min_active=0)
    assert evaluate_genome(p, 0).survivors == 4
    assert evaluate_genome(p, 2).survivors == 2
    assert optimize(p,method='ga_cs',evaluations=20,seed=11).best.survivors <=4


def test_rejects_invalid_problem_and_parameters():
    with pytest.raises(ValueError): SearchProblem((1,),('x',),universe_size=0,target=1,min_survivors=1,max_survivors=1)
    with pytest.raises(ValueError): SearchProblem((1,),('x','y'),universe_size=4,target=1,min_survivors=1,max_survivors=1)
    with pytest.raises(ValueError): SearchProblem((16,),('x',),universe_size=4,target=1,min_survivors=1,max_survivors=2)
    with pytest.raises(ValueError): SearchProblem((1,),('x',),universe_size=4,target=8,min_survivors=1,max_survivors=4)
    with pytest.raises(ValueError): optimize(fixture_problem(),method='bogus',evaluations=10)
    with pytest.raises(ValueError): optimize(fixture_problem(),method='ga_cs',evaluations=0)
    with pytest.raises(ValueError): optimize(fixture_problem(),method='ga_cs',evaluations=40,switch_ratio=1.1)
