"""V3.7.34 independent brute-force interaction and conservation oracles."""
from fractions import Fraction
from itertools import permutations
import math

import pytest

from pailie5.ga_cs_optimizer_v3715 import SearchProblem
from pailie5.filter_interactions_v3734 import audit_filter_interactions


def problem(masks, *, n=8, hard=None):
    return SearchProblem(
        masks=tuple(masks),
        rule_names=tuple(f"r{i}" for i in range(len(masks))),
        universe_size=n, target=1, min_survivors=1,
        max_survivors=n, min_active=0, hard_mask=hard,
    )


def brute_shapley(p):
    full = (1 << p.universe_size) - 1 if p.hard_mask is None else p.hard_mask
    contributions = [Fraction(0) for _ in p.masks]
    for order in permutations(range(len(p.masks))):
        current = full
        for i in order:
            next_mask = current & p.masks[i]
            contributions[i] += current.bit_count() - next_mask.bit_count()
            current = next_mask
    return [x / math.factorial(len(p.masks)) for x in contributions]


def fractions(report):
    return [Fraction(row["shapley_excluded_numerator"],
                     row["shapley_excluded_denominator"])
            for row in report["shapley"]]


def test_overlap_identity_diminishing_returns_and_exact_attribution():
    p = problem((0b00111111, 0b00011111))
    output = audit_filter_interactions(p)
    assert output == audit_filter_interactions(p)
    assert output["hard_mask_survivors"] == 8
    assert output["all_rules_survivors"] == 5
    assert output["all_rules_excluded"] == 3
    pair = output["pairwise"][0]
    assert pair["left_excluded"] == 2
    assert pair["right_excluded"] == 3
    assert pair["both_excluded"] == 3
    assert pair["overlap_excluded"] == 2
    assert pair["new_exclusions_right_after_left"] == 1
    assert pair["new_exclusions_left_after_right"] == 0
    assert pair["excluded_jaccard"] == {"numerator": 2, "denominator": 3}
    assert output["minimum_diminishing_returns_gap"] == 2
    assert output["submodularity_squares_checked"] == 1
    assert fractions(output) == [Fraction(1), Fraction(2)]
    assert sum(fractions(output)) == 3
    assert not output["historical_outcomes_read"]
    assert not output["forecasting_performed"]


def test_duplicate_rules_shares_and_zero_additional_value():
    p = problem((0b00001111, 0b00001111))
    r = audit_filter_interactions(p)
    assert r["all_rules_excluded"] == 4
    assert r["pairwise"][0]["exact_duplicate_exclusions"]
    assert r["pairwise"][0]["new_exclusions_right_after_left"] == 0
    assert fractions(r) == [Fraction(2), Fraction(2)]


def test_independent_excluded_sets_have_zero_overlap_and_exact_zero_gap():
    p = problem((0b11111110, 0b11111101))
    r = audit_filter_interactions(p)
    assert r["all_rules_excluded"] == 2
    assert r["pairwise"][0]["overlap_excluded"] == 0
    assert r["minimum_diminishing_returns_gap"] == 0
    assert fractions(r) == [Fraction(1), Fraction(1)]


def test_empty_masks_and_hard_mask_are_never_silently_repaired():
    p = problem((0, 0b11111111), hard=0b00001111)
    r = audit_filter_interactions(p)
    assert r["hard_mask_survivors"] == 4
    assert r["all_rules_survivors"] == 0
    assert fractions(r) == [Fraction(4), Fraction(0)]
    assert r["shapley"][1]["zero_independent_contribution"]


def test_brute_permutation_oracle_all_three_rule_shares():
    p = problem((0b11110011, 0b10011001, 0b00111100))
    r = audit_filter_interactions(p)
    assert fractions(r) == brute_shapley(p)
    assert r["submodularity_squares_checked"] == 6
    assert len(r["inventory_sha256"]) == 64


def test_mask_provenance_hash_changes_if_any_rule_or_hard_mask_changes():
    a = audit_filter_interactions(problem((0b1111, 0b1100)))
    b = audit_filter_interactions(problem((0b1111, 0b1000)))
    c = audit_filter_interactions(problem((0b1111, 0b1100), hard=0b1111))
    assert len({a["inventory_sha256"], b["inventory_sha256"],
                c["inventory_sha256"]}) == 3


def test_full_100000_domain_with_three_static_masks():
    a = (1 << 10000) - 1
    b = sum(((1 << 1000) - 1) << (i * 10000) for i in range(10))
    c = sum(((1 << 100) - 1) << (i * 1000) for i in range(100))
    r = audit_filter_interactions(problem((a, b, c), n=100000))
    assert r["all_rules_survivors"] == 100
    assert r["all_rules_excluded"] == 99900
    assert sum(fractions(r)) == 99900
    assert r["pairs_checked"] == 3
    assert r["static_and_monotone_submodular"]
    assert not r["historical_coverage_measured"]


def test_rejects_inventory_above_exact_scope():
    p = problem((255,) * 13)
    with pytest.raises(ValueError, match="capped"):
        audit_filter_interactions(p)
