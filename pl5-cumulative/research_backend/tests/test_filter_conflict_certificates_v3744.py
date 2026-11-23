"""V3.7.44 adversarial and exact-enumeration filter conflict oracles."""
from copy import deepcopy
from functools import lru_cache

import pytest

from pailie5.filter_fair_longitudinal_v3743 import run_longitudinal
from pailie5.filter_conflict_certificates_v3744 import (
    ALL_MASK, METHOD_COUNT, _minimal_cores, build_conflict_certificates,
    verify_conflict_certificates,
)


@lru_cache(maxsize=2)
def evidence():
    return run_longitudinal(windows=4)


@lru_cache(maxsize=2)
def certificates():
    return build_conflict_certificates(evidence())


def test_complete_subset_lattice_crosschecked_independently():
    source = evidence()
    report = certificates()
    verify_conflict_certificates(source, report)
    assert report == build_conflict_certificates(source)
    assert report["window_count"] == 4
    assert report["subset_count_per_window"] == ALL_MASK == 63
    assert report["summary"]["pairwise_comparisons"] == 4 * 15
    assert report["summary"]["six_way_empty_windows"] == 4
    assert report["uses_observed_ids_for_combination_calculation"] is False
    for row, source_row in zip(report["windows"], source["records"]):
        assert row["issue"] == source_row["issue"]
        assert row["frozen_panel_sha256"] == source_row["panel"]["payload_sha256"]
        assert len(row["subset_certificates"]) == 63
        assert [r["subset_mask"] for r in row["subset_certificates"]] == list(range(1, 64))
        assert all(r["retained_count"] <= 100 for r in row["subset_certificates"])
        assert all(r["retained_count"] == 100 for r in row["subset_certificates"]
                   if r["subset_mask"].bit_count() == 1)
        sets = [set(m["candidate_ids"]) for m in source_row["panel"]["payload"]["methods"]]
        for r in row["subset_certificates"]:
            selected = [sets[i] for i in range(METHOD_COUNT) if r["subset_mask"] & (1 << i)]
            assert len(set.intersection(*selected)) == r["retained_count"]
        assert all(sum(1 for i in range(METHOD_COUNT) if core & (1 << i)) >= 2
                   for core in row["minimal_conflict_masks"])


def test_genuine_three_way_minimal_conflict_not_shadowed_by_pairwise_conflict():
    sets = [
        {"00001", "00002"}, {"00002", "00003"}, {"00001", "00003"},
        {"00001", "00002", "00003"}, {"00001", "00002", "00003"},
        {"00001", "00002", "00003"},
    ]
    counts = {
        mask: len(set.intersection(*(sets[i] for i in range(METHOD_COUNT)
                                     if mask & (1 << i))))
        for mask in range(1, ALL_MASK + 1)
    }
    assert counts[1 | 2] == counts[1 | 4] == counts[2 | 4] == 1
    assert _minimal_cores(counts) == [7]


def test_pairwise_conflict_is_minimal_and_its_supersets_are_not():
    sets = [{"00001"}, {"00002"}] + [{"00001", "00002"}] * 4
    counts = {mask: len(set.intersection(*(sets[i] for i in range(METHOD_COUNT)
                                             if mask & (1 << i))))
              for mask in range(1, ALL_MASK + 1)}
    assert _minimal_cores(counts) == [3]


def test_rejects_missing_or_invalid_subset_lattice():
    with pytest.raises(ValueError):
        _minimal_cores({1: 100})
    with pytest.raises(ValueError):
        _minimal_cores({mask: (-1 if mask == 1 else 0)
                        for mask in range(1, ALL_MASK + 1)})


def test_fail_closed_on_tampering_with_any_frozen_conflict_certificate():
    source = evidence()
    report = certificates()
    changes = (
        lambda x: x["windows"].reverse(),
        lambda x: x["windows"].pop(),
        lambda x: x["windows"][0]["subset_certificates"][2].update({"retained_count": 1}),
        lambda x: x["windows"][0]["subset_certificates"][0].update({"candidate_bitmap_sha256": "0" * 64}),
        lambda x: x["windows"][0]["subset_certificates"].pop(0),
        lambda x: x["windows"][0].update({"minimal_conflict_masks": []}),
        lambda x: x["summary"].update({"pairwise_empty_intersections": 999}),
        lambda x: x.update({"frozen_source_chain_sha256": "0" * 64}),
        lambda x: x.update({"candidate_budget_per_method": 99}),
        lambda x: x.update({"method_order": list(reversed(x["method_order"]))}),
    )
    for change in changes:
        tampered = deepcopy(report)
        change(tampered)
        with pytest.raises(ValueError):
            verify_conflict_certificates(source, tampered)


def test_full_24_window_regression_is_stable_and_preserves_negative_results():
    source = run_longitudinal(windows=24)
    report = build_conflict_certificates(source)
    assert report["frozen_source_chain_sha256"] == "6b9f96e6f1a4f38b60f7ca1f50d927e63049c8da8a22ccf253bdbcd76727ecd3"
    assert report["summary"]["pairwise_comparisons"] == 360
    assert report["summary"]["pairwise_empty_intersections"] == 255
    assert report["summary"]["six_way_empty_windows"] == 24
    assert report["summary"]["minimal_conflicts_by_size"]["2"] == 255
    assert report["summary"]["minimal_conflicts_by_size"]["3"] == 1
    assert report["summary"]["windows_with_genuine_three_way_minimal_conflict"] == 1
    triple = [r for r in report["windows"] if 37 in r["minimal_conflict_masks"]]
    assert len(triple) == 1 and triple[0]["issue"] == "000992"
    verify_conflict_certificates(source, report)
