"""Independent permutation and set-membership checks for weighted order."""
from itertools import permutations
from random import Random

import pytest

from pailie5.weighted_filter_order_v3746 import audit_weighted_order


def oracle(masks, costs, n, hard):
    rules = [{j for j in range(n) if mask & (1 << j)} for mask in masks]
    initial = {j for j in range(n) if hard & (1 << j)}
    def run(order):
        active = initial.copy()
        work = 0
        for i in order:
            work += len(active) * costs[i]
            active &= rules[i]
        return work, order, len(active)
    return min(run(p) for p in permutations(range(len(masks))))


def test_counterexample_to_cost_and_greedy_order():
    masks = (3346, 3078, 3417, 1103)
    result = audit_weighted_order(masks, (2, 4, 5, 6), universe_size=12)
    assert result["optimal"]["order"] == [0, 3, 2, 1]
    assert result["optimal"]["weighted_cost"] == 68
    assert result["baselines"]["cost_only"]["weighted_cost"] == 71
    assert result["baselines"]["greedy_exclusion_per_cost"]["weighted_cost"] == 71
    assert result["retained"] == 1
    assert result["transitions_per_solve"] == 32


def test_randomized_exact_oracle_with_hard_masks_and_empty_intersections():
    rng = Random(3746)
    for m in range(1, 7):
        for _ in range(5):
            n = 17
            masks = tuple(rng.randrange(1 << n) for _ in range(m))
            costs = tuple(rng.randrange(1, 9) for _ in masks)
            hard = rng.randrange(1 << n)
            expected = oracle(masks, costs, n, hard)
            actual = audit_weighted_order(masks, costs, universe_size=n, hard_mask=hard)
            assert (actual["optimal"]["weighted_cost"],
                    tuple(actual["optimal"]["order"]), actual["retained"]) == expected
            for plan in (actual["optimal"], *actual["baselines"].values()):
                assert plan["stages"][-1]["retained"] == expected[2]
                assert plan["weighted_cost"] >= expected[0]


def test_legacy_full_domain_sensitivity_without_historical_input():
    from pailie5.affine_recurrence_filters_v3739 import recurrence_keep_masks
    masks = recurrence_keep_masks()
    report = audit_weighted_order(masks, (5, 2, 1))
    assert report["retained"] == 100
    assert report["optimal"]["order"] == [2, 1, 0]
    assert report["optimal"]["weighted_cost"] == 125000
    assert report["baselines"]["equal_unit_optimal"]["weighted_cost"] == 521000
    assert report["baselines"]["cost_only"]["weighted_cost"] == 125000
    assert report["baselines"]["greedy_exclusion_per_cost"]["weighted_cost"] == 125000
    assert report["historical_coverage_measured"] is False
    assert report["wall_clock_measured"] is False
    equal = audit_weighted_order(masks, (1, 1, 1))
    assert equal["optimal"]["weighted_cost"] == 111000
    assert equal["optimal"]["order"] == [0, 1, 2]
    assert equal["final_mask_sha256"] == report["final_mask_sha256"]


def test_zero_hard_mask_and_deterministic_ties():
    result = audit_weighted_order((7, 7, 7), (3, 2, 1), universe_size=3, hard_mask=0)
    assert result["optimal"]["order"] == [0, 1, 2]
    assert result["optimal"]["weighted_cost"] == 0
    assert result["retained"] == 0


@pytest.mark.parametrize("masks,costs,n,hard", [
    ((), (), 3, None), ((1,), (), 3, None),
    ((8,), (1,), 3, None), ((-1,), (1,), 3, None),
    ((True,), (1,), 3, None), ((1,), (0,), 3, None),
    ((1,), (True,), 3, None), ((1,), (1.0,), 3, None),
    ((1,), (10**9 + 1,), 3, None), ((1,), (1,), 0, None),
    ((1,), (1,), 3, 8), ((1,) * 13, (1,) * 13, 3, None),
])
def test_fail_closed_inputs(masks, costs, n, hard):
    with pytest.raises(ValueError):
        audit_weighted_order(masks, costs, universe_size=n, hard_mask=hard)
