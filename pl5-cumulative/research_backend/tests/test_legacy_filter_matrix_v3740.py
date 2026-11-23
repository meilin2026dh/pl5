"""V3.7.40 source-complete library census and unified synthetic filter matrix."""
from functools import lru_cache
import json

import numpy as np
import pytest

from pailie5.basic_filters import BasicConstraint, apply_basic_filters
from pailie5.legacy_method_census_v3740 import inventory
from pailie5.legacy_filter_matrix_v3740 import (
    DOMAIN, SAMPLE_PERIODS, _mask_from_ids, _mask_sha256, _synthetic_records, run,
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


def test_synthetic_fixture_digest_and_safety_scope():
    draws, source = _synthetic_records()
    assert source["row_count"] == len(draws)
    assert source["first_issue"] == draws[0][0]
    assert source["last_issue"] == draws[-1][0]
    assert draws[0][1] == "55096"
    assert source["source_path"] == "data/synthetic_demo.csv"
