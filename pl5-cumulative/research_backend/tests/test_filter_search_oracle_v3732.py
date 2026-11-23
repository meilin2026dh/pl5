"""V3.7.32 filter-search oracle tests: no historical draw data."""
import copy

import pytest

from pailie5.ga_cs_optimizer_v3715 import SearchProblem, evaluate_genome
from pailie5.filter_search_oracle_v3732 import compare_search_to_exact_oracle


def tiny_problem(*, hard=None):
    return SearchProblem(
        masks=(0b0011111111111111, 0b1111000011110000,
               0b1010101010101010, 0b0111100011110000),
        rule_names=("a", "b", "c", "d"),
        universe_size=16, target=3, min_survivors=1,
        max_survivors=8, min_active=1, hard_mask=hard,
    )


def test_same_objective_exact_oracle_complete_and_budget_equal():
    p = tiny_problem()
    result = compare_search_to_exact_oracle(p, seeds=(7, 8, 9), evaluations=24)
    expected = max((evaluate_genome(p, mask) for mask in range(1 << 4)),
                   key=lambda x: (float(x.feasible), x.fitness, -x.genome))
    assert result["oracle"] == {
        "evaluations": 16, "best_genome": expected.genome,
        "survivors": expected.survivors, "feasible": expected.feasible,
        "fitness": expected.fitness, "rule_count": expected.rule_count,
    }
    assert result == compare_search_to_exact_oracle(p, seeds=(7, 8, 9), evaluations=24)
    assert len(result["inventory_sha256"]) == 64
    for row in result["trials"]:
        assert set(row["arms"]) == {"random", "ga_cs"}
        for arm in row["arms"].values():
            assert arm["evaluations"] == 24
            assert sum(arm["stage_evaluations"].values()) == 24
            assert arm["fitness"] <= expected.fitness or not expected.feasible
    assert result["historical_coverage_measured"] is False
    assert result["forecasting_performed"] is False
    assert result["future_advantage_claim"] is False


def test_fixed_hard_mask_changes_manifest_and_never_leaks_candidates():
    original = compare_search_to_exact_oracle(tiny_problem(), seeds=(1,), evaluations=12)
    restricted = compare_search_to_exact_oracle(tiny_problem(hard=0b1111111100000000),
                                                seeds=(1,), evaluations=12)
    assert original["inventory_sha256"] != restricted["inventory_sha256"]
    assert restricted["rule_inventory"]["hard_mask_sha256"] is not None
    assert all((evaluate_genome(tiny_problem(hard=0b1111111100000000),
                                row["arms"][method]["best_genome"]).survivors
                == row["arms"][method]["survivors"])
               for row in restricted["trials"] for method in ("random", "ga_cs"))


def test_full_100k_identity_space_compares_exactly_and_no_draws():
    a = (1 << 10000) - 1
    b = sum(((1 << 1000) - 1) << (i * 10000) for i in range(10))
    c = sum(((1 << 100) - 1) << (i * 1000) for i in range(100))
    p = SearchProblem(masks=(a, b, c), rule_names=("d0", "d1", "d2"),
                      universe_size=100000, target=100, min_survivors=1,
                      max_survivors=100, min_active=1)
    result = compare_search_to_exact_oracle(p, seeds=(11, 12), evaluations=12)
    assert result["oracle"]["evaluations"] == 8
    assert result["oracle"]["feasible"]
    assert result["oracle"]["survivors"] == 100
    assert result["evaluation_budget_per_arm"] == 12
    assert result["evidence"] == "INTERNAL_FROZEN_MASK_OPTIMIZATION_ONLY"


@pytest.mark.parametrize("kwargs", [
    {"seeds": ()}, {"seeds": (1, 1)}, {"seeds": (True,)},
    {"seeds": [1]}, {"evaluations": 0}, {"evaluations": True},
    {"switch_ratio": 0}, {"switch_ratio": 1}, {"switch_ratio": float("nan")},
])
def test_protocol_fail_closed(kwargs):
    with pytest.raises(ValueError):
        compare_search_to_exact_oracle(tiny_problem(), **kwargs)


def test_more_than_twelve_rule_inventory_rejected():
    p = SearchProblem(masks=(0b1111,) * 13,
                      rule_names=tuple(f"r{i}" for i in range(13)),
                      universe_size=16, target=1,
                      min_survivors=1, max_survivors=16)
    with pytest.raises(ValueError, match="limit"):
        compare_search_to_exact_oracle(p)
