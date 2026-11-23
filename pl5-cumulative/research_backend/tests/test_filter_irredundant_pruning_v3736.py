"""V3.7.36 large-rule proof and falsification: static masks only."""
import random

import pytest

from pailie5.ga_cs_optimizer_v3715 import SearchProblem
from pailie5.filter_irredundant_pruning_v3736 import prune_inclusion_minimal
from pailie5.filter_equivalent_pruning_v3735 import exact_equivalent_pruning


def make_problem(masks, n=12, hard=None):
    return SearchProblem(
        masks=tuple(masks),
        rule_names=tuple(f"rule_{i}" for i in range(len(masks))),
        universe_size=n,
        target=1,
        min_survivors=1,
        max_survivors=n,
        hard_mask=hard,
    )


def mask_of(problem, indices):
    result = ((1 << problem.universe_size) - 1
              if problem.hard_mask is None else problem.hard_mask)
    for i in indices:
        result &= problem.masks[i]
    return result


def verify_result(problem, report):
    baseline = mask_of(problem, range(len(problem.masks)))
    indices = report["kept_rule_indices"]
    assert mask_of(problem, indices) == baseline
    assert report["original_full_bitmap_sha256"] == report["simplified_bitmap_sha256"]
    assert len(indices) == report["optional_rule_count_after"]
    for witness in report["retained_rule_necessity_witnesses"]:
        without = mask_of(problem, (i for i in indices if i != witness["rule_index"]))
        gained = without & ~baseline
        assert gained.bit_count() == witness["new_candidates_if_removed"]
        assert gained & (1 << witness["first_restored_candidate_index"])
    assert report["all_remaining_rules_individually_necessary"]
    assert report["global_minimum_rule_count_proven"] is False
    assert not report["historical_outcomes_read"]


def test_fixed_duplicate_and_100k_full_domain_deterministic():
    a = (1 << 10000) - 1
    b = sum(((1 << 1000) - 1) << (i * 10000) for i in range(10))
    c = sum(((1 << 100) - 1) << (i * 1000) for i in range(100))
    p = make_problem((a, b, c, a, b, c), n=100_000)
    r = prune_inclusion_minimal(p)
    assert r == prune_inclusion_minimal(p)
    assert r["chosen_bitmap_survivors"] == 100
    assert r["optional_rule_count_after"] == 3
    verify_result(p, r)


def test_sixty_rule_scalability_and_necessity_checks():
    n = 60
    p = make_problem(tuple(((1 << n) - 1) ^ (1 << i) for i in range(n)), n=n)
    r = prune_inclusion_minimal(p)
    assert r["optional_rule_count_after"] == n
    assert not r["removed_rule_indices"]
    assert r["chosen_bitmap_survivors"] == 0
    assert all(w["new_candidates_if_removed"] == 1 for w in r["retained_rule_necessity_witnesses"])
    verify_result(p, r)


def test_inclusion_minimal_not_globally_smallest_counterexample():
    p = make_problem((0b100, 0b001, 0b000), n=3)
    greedy = prune_inclusion_minimal(p, priority=(2, 0, 1))
    exact = exact_equivalent_pruning(p)
    assert greedy["kept_rule_indices"] == [0, 1]
    assert greedy["optional_rule_count_after"] == 2
    assert exact["chosen_rule_count"] == 1
    assert exact["chosen_genome"] == 4
    verify_result(p, greedy)


def test_generated_small_cases_crosscheck_exact_bitmap_oracle():
    rng = random.Random(3736)
    for _ in range(30):
        p = make_problem(tuple(rng.randrange(1 << 9) for _ in range(6)),
                         n=9, hard=rng.randrange(1 << 9))
        r = prune_inclusion_minimal(p)
        verify_result(p, r)
        exact = exact_equivalent_pruning(p)
        assert r["optional_rule_count_after"] >= exact["chosen_rule_count"]
        assert r["chosen_bitmap_survivors"] == exact["all_rules_survivors"]


def test_hard_mask_may_make_all_rules_disposable():
    p = make_problem((0b11111100, 0b11110000), n=8, hard=0b00000011)
    r = prune_inclusion_minimal(p)
    assert r["kept_rule_indices"] == [0]
    assert r["chosen_bitmap_survivors"] == 0
    verify_result(p, r)


@pytest.mark.parametrize("order", [(), (0, 0), (0, 2), (True, 1), [0, 1]])
def test_bad_priority_rejected(order):
    p = make_problem((7, 3), n=4)
    with pytest.raises(ValueError):
        prune_inclusion_minimal(p, priority=order)


def test_more_than_sixty_rules_refused_by_shared_search_problem_contract():
    # SearchProblem itself rejects >60 rules before our bounded pruner is called.
    with pytest.raises(ValueError, match="60"):
        make_problem((7,) * 61, n=3)
