"""V3.7.40 source-complete library census and unified synthetic filter matrix."""
from functools import lru_cache
import json

import numpy as np
import pytest

from pailie5.basic_filters import BasicConstraint, apply_basic_filters
from pailie5.legacy_method_census_v3740 import inventory
from pailie5.legacy_filter_matrix_v3740 import (
    DOMAIN, SAMPLE_PERIODS, _mask_from_ids, _mask_sha256,
    _minimum_cardinality_certificate, _synthetic_records, run,
)


@lru_cache(maxsize=1)
def report():
    return run()


def test_fail_closed_census_tracks_every_repository_source_module():
    source = inventory()
    assert source["tracked_package_modules"] >= 90
    assert source["tracked_test_files"] >= 100
    assert not source["missing_registration"]
    assert len({x["name"] for x in source["source_rows"]}) == source["tracked_package_modules"]
    assert all(len(x["source_sha256"]) == 64 for x in source["source_rows"])
    assert all(x["role"] in {
        "candidate_filters", "combination_optimizers",
        "mathematical_operator_research", "historical_evaluation_and_evidence",
        "infrastructure",
    } for x in source["source_rows"])
    assert source["historical_actual_records_checked"] is False


def test_matrix_measures_legacy_mapped_structure_and_fixed_pattern_families():
    data = report()
    assert data["census"]["tracked_package_modules"] >= 90
    assert data["measured_static_arms"] == len(data["static_mask_arms"])
    assert len({x["name"] for x in data["static_mask_arms"]}) == data["measured_static_arms"]
    assert data["static_family_counts"]["basic_static"] >= 20
    assert data["static_family_counts"]["mapped_static"] >= 25
    assert data["static_family_counts"]["dsc_structure"] == 5
    assert data["static_family_counts"]["affine_recurrence"] == 3
    assert data["measured_time_forward_pattern_arms"] == 6
    assert data["measured_fixed_k_rank_arms"] == 6
    assert data["trusted_real_historical_comparison_complete"] is False
    assert data["source"]["source_kind"] == "INTERNAL_SYNTHETIC_DEMO_NOT_AUTHENTICATED_HISTORY"
    assert len(data["source"]["source_sha256"]) == 64
    assert len(data["non_direct_filter_components"]) + sum(
        int(x["direct_mask_adapter_in_v3740"]) for x in data["census"]["source_rows"]
    ) == data["census"]["tracked_package_modules"]


def test_complete_ledger_and_exact_count_bounds():
    data = report()
    n = data["source"]["row_count"]
    for item in data["static_mask_arms"]:
        assert 0 <= item["kept_count"] <= DOMAIN
        assert item["excluded_count"] + item["kept_count"] == DOMAIN
        assert item["demo_evaluated"] == n
        assert 0 <= item["demo_contained"] <= n
        assert len(item["candidate_mask_sha256"]) == 64
    for family in data["time_forward_synthetic_pattern_arms"]:
        assert len(family["runs"]) == SAMPLE_PERIODS
        assert family["total_synthetic_contained"] == sum(
            int(x["synthetic_contained"]) for x in family["runs"]
        )
        assert all(1 <= x["retained_count"] <= DOMAIN for x in family["runs"])
        assert all(len(x["candidate_sha256"]) == 64 for x in family["runs"])
        assert all(len(x["past_sha256"]) == 64 for x in family["runs"])
        assert all(x["past_rows"] < n for x in family["runs"])
    for arm in data["time_forward_synthetic_fixed_k_rank_arms"]:
        assert arm["evaluation_periods"] == SAMPLE_PERIODS
        assert arm["fixed_candidate_budget"] == 100
        assert len(arm["runs"]) == SAMPLE_PERIODS
        assert all(x["retained_count"] == 100 for x in arm["runs"])
        assert arm["total_synthetic_contained"] == sum(
            int(x["synthetic_contained"]) for x in arm["runs"]
        )
    assert json.loads(json.dumps(data)) == data


def test_basic_filter_adapter_is_actual_legacy_rule_and_not_reconstructed_score():
    data = report()
    row = next(x for x in data["static_mask_arms"]
               if x["name"] == "legacy.sum.central_quantile_band")
    expected = apply_basic_filters([
        BasicConstraint("sum", minimum=row["minimum"], maximum=row["maximum"])
    ])
    assert row["kept_count"] == len(expected)
    assert row["candidate_mask_sha256"] == _mask_sha256(_mask_from_ids(expected))
    assert row["adapter"] == "BasicConstraint"


def test_greedy_combination_only_structural_no_labels_or_hidden_quota_repair():
    data = report()
    result = data["greedy_combination"]
    counts = [x["retained"] for x in result["stages"]]
    assert len(counts) == len(result["selected_rules"]) <= 12
    assert all(0 < a < b for a, b in zip(counts, [DOMAIN] + counts[:-1]))
    assert result["retained"] == (counts[-1] if counts else DOMAIN)
    assert result["target_at_most_100_met"] == (0 < result["retained"] <= 100)
    assert result["global_optimum_claim"] is False
    assert data["original_historical_digests_changed"] is False


@pytest.mark.parametrize("invalid", [np.array([1, 1], dtype=np.int32),
                                      np.array([-1], dtype=np.int32),
                                      np.array([100000], dtype=np.int32),
                                      np.array([1.5]),
                                      np.array([[1]])])
def test_reject_wrong_candidate_ids(invalid):
    with pytest.raises(ValueError):
        _mask_from_ids(invalid)



def test_minimum_rule_certificate_three_rule_small_domain_oracle():
    # All pair intersections keep two IDs, the triple keeps exactly one.
    def keep(*ids):
        return sum(1 << i for i in ids)
    masks = [
        ("a", keep(0, 1, 2, 3)),
        ("b", keep(0, 1, 4, 5)),
        ("c", keep(0, 2, 4, 6)),
    ]
    proof = _minimum_cardinality_certificate(
        masks, ["a", "b", "c"], domain_size=8, target=1)
    assert proof["is_proposed_witness_cardinality_minimal"]
    assert proof["certified_minimum_rule_count"] == 3
    assert proof["strictly_smaller_subsets_examined"] == 7  # C(3,0)+C(3,1)+C(3,2)
    assert [x["minimum_nonempty_retained"]
            for x in proof["smaller_cardinality_audit"]] == [8, 4, 2]
    assert proof["witness_count"] == 1
    assert not proof["historical_coverage_measured"]


def test_minimum_rule_certificate_rejects_nonminimal_witness_and_empty_shortcuts():
    def keep(*ids):
        return sum(1 << i for i in ids)
    masks = [("a", keep(0, 1)), ("b", keep(2, 3)),
             ("c", keep(0, 2))]
    # a & b is empty and MUST NOT be counted as a successful target.
    proof = _minimum_cardinality_certificate(
        masks, ["a", "c"], domain_size=4, target=1)
    assert proof["certified_minimum_rule_count"] == 2
    assert proof["is_proposed_witness_cardinality_minimal"]
    assert proof["smaller_cardinality_audit"][1]["minimum_nonempty_retained"] == 2
    with pytest.raises(ValueError, match="proposed witness"):
        _minimum_cardinality_certificate(
            masks, ["a"], domain_size=4, target=1)

    # A redundant third rule cannot conceal a valid two-rule subset.
    masks2 = [("a", keep(0, 1)), ("b", keep(0, 2)),
              ("c", keep(0, 3))]
    nonminimal = _minimum_cardinality_certificate(
        masks2, ["a", "b", "c"], domain_size=4, target=1)
    assert nonminimal["certified_minimum_rule_count"] == 2
    assert not nonminimal["is_proposed_witness_cardinality_minimal"]
    assert nonminimal["first_smaller_feasible_witness"]["names"] == ["a", "b"]


@pytest.mark.parametrize("masks,selected", [
    ([("a", 3), ("a", 1)], ["a"]),
    ([("a", -1)], ["a"]),
    ([("a", 16)], ["a"]),
    ([("a", 3)], ["missing"]),
    ([("a", 3)], ["a", "a"]),
])
def test_minimum_rule_certificate_fails_closed_on_invalid_inventory(masks, selected):
    with pytest.raises(ValueError):
        _minimum_cardinality_certificate(
            masks, selected, domain_size=4, target=1)


def test_full_58_filter_matrix_exact_minimum_cardinality_certificate():
    data = report()
    proof = data["minimum_rule_cardinality_certificate"]
    assert proof["available_frozen_rules"] == data["measured_static_arms"] == 58
    assert proof["strictly_smaller_subsets_examined"] == 1 + 58 + 58 * 57 // 2
    assert proof["witness_rules"] == data["greedy_combination"]["selected_rules"]
    assert proof["witness_count"] == data["greedy_combination"]["retained"] == 100
    assert proof["witness_sha256"] == data["greedy_combination"]["final_mask_sha256"]
    assert proof["is_proposed_witness_cardinality_minimal"]
    assert proof["certified_minimum_rule_count"] == 3
    assert proof["first_smaller_feasible_witness"] is None
    assert proof["historical_coverage_measured"] is False


def test_synthetic_fixture_digest_and_safety_scope():
    draws, source = _synthetic_records()
    assert source["row_count"] == len(draws)
    assert source["first_issue"] == draws[0][0]
    assert source["last_issue"] == draws[-1][0]
    assert draws[0][1] == "55096"
    assert source["source_path"] == "data/synthetic_demo.csv"


def test_three_rule_frontier_independent_set_oracle():
    from itertools import combinations
    from collections import Counter
    from pailie5.legacy_filter_matrix_v3740 import _three_rule_frontier
    sets = {"a": {0, 1, 2}, "b": {0, 1, 3}, "c": {0, 1, 4},
            "d": {0, 1, 2}, "e": {5, 6}, "f": {0, 2, 3}}
    masks = [(name, sum(1 << x for x in ids)) for name, ids in sets.items()]
    report = _three_rule_frontier(masks, domain_size=8, target=2)
    expected = Counter()
    classes = {}
    for triple in combinations(sorted(sets), 3):
        ids = frozenset.intersection(*(frozenset(sets[name]) for name in triple))
        expected[str(len(ids))] += 1
        if 0 < len(ids) <= 2:
            classes.setdefault(ids, []).append(list(triple))
    assert report["retained_count_histogram"] == dict(expected)
    assert report["triples_examined"] == 20
    assert report["empty_intersections"] > 0
    assert report["feasible_portfolios"] == sum(map(len, classes.values()))
    assert report["distinct_feasible_candidate_sets"] == len(classes)
    assert report["feasible_portfolios"] > report["distinct_feasible_candidate_sets"]
    assert {tuple(tuple(t) for t in group["portfolios"])
            for group in report["equivalence_classes"]} == {
            tuple(tuple(t) for t in v) for v in classes.values()}
    assert report["exact_target_portfolios"] == expected["2"]
    assert report["exact_target_distinct_sets"] == sum(len(ids) == 2 for ids in classes)
    assert report["best_nonempty_retained_at_or_below_target"] == 2
    assert report == _three_rule_frontier(masks[::-1], domain_size=8, target=2)


def test_three_rule_frontier_empty_result_and_equal_count_distinct_sets():
    from pailie5.legacy_filter_matrix_v3740 import _three_rule_frontier
    no_result = _three_rule_frontier([("a", 1), ("b", 2), ("c", 4)],
                                     domain_size=8, target=1)
    assert no_result["empty_intersections"] == 1
    assert no_result["feasible_portfolios"] == 0
    assert no_result["best_nonempty_retained_at_or_below_target"] is None
    result = _three_rule_frontier([("a", 3), ("b", 5), ("c", 6), ("d", 7)],
                                  domain_size=8, target=1)
    assert result["feasible_portfolios"] == 3
    assert result["distinct_feasible_candidate_sets"] == 3
    assert result["exact_target_distinct_sets"] == 3


@pytest.mark.parametrize("masks", [
    [("a", 1), ("a", 2), ("b", 3)],
    [("a", True), ("b", 2), ("c", 3)],
    [("a", 256), ("b", 2), ("c", 3)],
    [("a", 1), ("b", 2)],
])
def test_three_rule_frontier_rejects_invalid_masks(masks):
    from pailie5.legacy_filter_matrix_v3740 import _three_rule_frontier
    with pytest.raises(ValueError):
        _three_rule_frontier(masks, domain_size=8, target=1)


def test_full_three_rule_census_contains_existing_certificate():
    import math
    data = report()
    frontier = data["three_rule_frontier"]
    witness = data["minimum_rule_cardinality_certificate"]
    assert frontier["triples_examined"] == math.comb(58, 3) == 30856
    assert sum(frontier["retained_count_histogram"].values()) == 30856
    assert frontier["best_nonempty_retained_at_or_below_target"] == 100
    assert frontier["exact_target_portfolios"] >= 1
    assert frontier["distinct_feasible_candidate_sets"] <= frontier["feasible_portfolios"]
    assert frontier["exact_target_distinct_sets"] <= frontier["exact_target_portfolios"]
    assert any(group["candidate_sha256"] == witness["witness_sha256"]
               and sorted(witness["witness_rules"]) in group["portfolios"]
               for group in frontier["equivalence_classes"])
    assert not frontier["historical_coverage_measured"]
