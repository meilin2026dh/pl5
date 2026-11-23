"""V3.7.39 exact modular recurrence structure, all-domain and negative controls."""
import pytest

from pailie5.affine_recurrence_filters_v3739 import (
    RULE_NAMES, audit_recurrence_filters, recurrence_keep_masks,
)
from pailie5.digit_structure_v3737 import DOMAIN, _hash, reference_baseline
from pailie5.ga_cs_optimizer_v3715 import SearchProblem, evaluate_genome


def _contains(bits, number):
    return bool((bits >> number) & 1)


def test_constructive_rank_and_conjunction_cardinality():
    masks = recurrence_keep_masks()
    full = (1 << DOMAIN) - 1
    assert len(masks) == len(RULE_NAMES) == 3
    assert [mask.bit_count() for mask in masks] == [10000] * 3
    for m in masks:
        assert not _contains(m, 99999)
    current = full
    for mask, expected in zip(masks, (10000, 1000, 100)):
        current &= mask
        assert current.bit_count() == expected
    expected = set()
    for a in range(10):
        for b in range(10):
            x = [a, b]
            for _ in range(3):
                x.append((x[-1] + x[-2]) % 10)
            expected.add(int("".join(map(str, x))))
    assert len(expected) == 100
    actual = {i for i in range(DOMAIN) if _contains(current, i)}
    assert actual == expected


def test_cross_engine_same_size_target_and_baseline_overlap():
    r = audit_recurrence_filters()
    assert r == audit_recurrence_filters()
    assert r["exact_100_id_cap_feasible"]
    assert r["constructive_enumeration_count"] == 100
    assert r["stage_counts"][-1]["after"] == 100
    assert r["exact_subsets_checked"] == 8
    assert len(r["full_mask_sha256"]) == 64
    assert 0 <= r["baseline_intersection_count"] <= 100
    assert r["baseline_overlap_excluded_count"] + r["baseline_intersection_count"] == 100
    assert not r["historical_data_read"]
    assert not r["historical_coverage_measured"]
    assert not r["algorithm_value_vs_existing_inventory_established"]


def test_independent_existing_genome_oracle_unique_feasible_three_rules():
    masks = recurrence_keep_masks()
    p = SearchProblem(
        masks=masks, rule_names=RULE_NAMES, universe_size=DOMAIN,
        target=100, min_survivors=1, max_survivors=100,
    )
    results = [evaluate_genome(p, i) for i in range(8)]
    assert [r.genome for r in results if r.feasible] == [7]
    assert results[7].survivors == 100


def test_rule_order_does_not_change_membership():
    masks = recurrence_keep_masks()
    x = (1 << DOMAIN) - 1
    y = x
    for bit in masks:
        x &= bit
    for bit in reversed(masks):
        y &= bit
    assert x == y
    assert _hash(x) == _hash(y)


def test_baseline_subset_never_creates_candidate_id():
    masks = recurrence_keep_masks()
    full = masks[0] & masks[1] & masks[2]
    conventional = reference_baseline()
    subset = conventional & full
    assert subset & ~full == 0
    assert subset & ~conventional == 0
