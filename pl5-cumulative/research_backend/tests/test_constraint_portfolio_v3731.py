"""Exact-mask filter-engineering acceptance and falsification tests (no draws)."""
from itertools import permutations

import pytest

from pailie5.ga_cs_optimizer_v3715 import SearchProblem, evaluate_genome
from pailie5.constraint_portfolio_v3731 import exact_filter_portfolio


def problem(masks, target=2, minimum=1, maximum=8, min_active=0, hard_mask=None,
            universe=8):
    return SearchProblem(
        masks=tuple(masks),
        rule_names=tuple(f"r{i}" for i in range(len(masks))),
        universe_size=universe, target=target, min_survivors=minimum,
        max_survivors=maximum, min_active=min_active, hard_mask=hard_mask,
    )


def scalar_cost(masks, order, n, hard=None):
    alive = (1 << n) - 1 if hard is None else hard
    checks = 0
    for idx in order:
        checks += alive.bit_count()
        alive &= masks[idx]
    return checks


def test_all_subsets_and_permutation_oracle_and_exact_frontier():
    masks = (0b00111111, 0b00011111, 0b11100011, 0b01010101)
    p = problem(masks, target=3, minimum=1, maximum=7)
    result = exact_filter_portfolio(p)
    rows = []
    for genome in range(1 << len(masks)):
        expected = evaluate_genome(p, genome)
        if expected.feasible:
            members = tuple(i for i in range(len(masks)) if genome & (1 << i))
            best_cost = min(scalar_cost(masks, order, 8)
                            for order in permutations(members))
            rows.append((genome, expected.survivors, len(members),
                         best_cost, abs(expected.survivors - p.target)))
    assert result["subset_count"] == 16
    assert result["feasible_subset_count"] == len(rows)
    assert result["frontier"]
    expected_frontier = []
    for row in rows:
        genome, count, active, cost, error = row
        dominated = any(
            other[0] != genome and other[4] <= error
            and other[2] <= active and other[3] <= cost
            and ((other[4], other[2], other[3]) != (error, active, cost)
                 or other[0] < genome)
            for other in rows
        )
        if not dominated:
            expected_frontier.append(row)
    assert set(x["genome"] for x in result["frontier"]) == set(
        x[0] for x in expected_frontier
    )
    for item in result["frontier"]:
        genome, count, active, cost, error = next(
            row for row in rows if row[0] == item["genome"]
        )
        assert (item["survivor_count"], item["active_rule_count"],
                item["scalar_evaluation_cost"], item["target_distance"]) == (
                    count, active, cost, error
                )
    expected_best = min(rows, key=lambda r: (r[4], r[3], r[2], r[0]))
    assert result["best"]["genome"] == expected_best[0]


def test_order_dp_beats_naive_greedy_on_a_concrete_counterexample():
    masks = (3 | 128, 5 | 128, 10 | 128)
    p = problem(masks, target=1, minimum=1, maximum=1, min_active=3)
    r = exact_filter_portfolio(p)
    best = r["best"]
    assert best["genome"] == 0b111
    assert best["survivor_count"] == 1
    assert best["scalar_evaluation_cost"] == 12
    assert best["optimal_rule_order"] == ("r1", "r2", "r0")
    assert scalar_cost(masks, (0, 1, 2), 8) == 13
    assert best["scalar_evaluation_cost"] == min(
        scalar_cost(masks, order, 8) for order in permutations(range(3))
    )


def test_exact_full_100000_identity_space_to_100_is_structural_only():
    first_zero = (1 << 10000) - 1
    second_zero = sum(((1 << 1000) - 1) << (i * 10000) for i in range(10))
    third_zero = sum(((1 << 100) - 1) << (i * 1000) for i in range(100))
    p = problem(
        (first_zero, second_zero, third_zero), target=100, minimum=1,
        maximum=100, min_active=1, universe=100_000,
    )
    a = exact_filter_portfolio(p)
    b = exact_filter_portfolio(p)
    assert a == b
    assert a["best"]["genome"] == 7
    assert a["best"]["survivor_count"] == 100
    assert a["fair_uniform_coverage_of_best"] == 0.001
    assert len(a["best_mask_sha256"]) == 64
    assert not a["historical_coverage_measured"]
    assert not a["future_advantage_claim"]


def test_hard_mask_cannot_be_switched_off():
    p = problem((0b11111111, 0b00001111), target=4, minimum=2,
                maximum=4, min_active=0, hard_mask=0b11110000)
    result = exact_filter_portfolio(p)
    assert result["hard_mask_survivors"] == 4
    assert result["best"]["genome"] == 0
    assert result["best"]["survivor_count"] == 4
    assert result["best"]["scalar_evaluation_cost"] == 0


def test_full_portfolio_drop_one_redunancy_exact_counts():
    p = problem((0b00001111, 0b00001111), target=4, minimum=4,
                maximum=4, min_active=2)
    result = exact_filter_portfolio(p)
    assert result["best"]["genome"] == 3
    assert [x["recoverable_if_removed"] for x in result["drop_one_diagnostics"]] == [0, 0]
    assert all(x["redundant_given_others"] for x in result["drop_one_diagnostics"])


def test_no_feasible_portfolio_and_mask_conflict_are_not_silently_repaired():
    p = problem((0b11110000, 0b00001111), target=1, minimum=1,
                maximum=1, min_active=2)
    result = exact_filter_portfolio(p)
    assert result["feasible_subset_count"] == 0
    assert result["best"] is None
    assert result["best_mask_sha256"] is None
    assert result["empty_subset_count"] == 1


def test_strict_capacity_guard_and_incorrect_input_types():
    p = problem((0b11,), target=1)
    for bound in (0, 13, 2.0, True):
        with pytest.raises(ValueError):
            exact_filter_portfolio(p, max_rules=bound)
    p13 = SearchProblem(
        masks=(1,) * 13, rule_names=tuple(f"r{i}" for i in range(13)),
        universe_size=8, target=1, min_survivors=1, max_survivors=1,
    )
    with pytest.raises(ValueError, match="capped"):
        exact_filter_portfolio(p13)
