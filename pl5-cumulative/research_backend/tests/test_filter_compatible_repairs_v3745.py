"""Independent exact-oracle and adversarial V3.7.45 tests."""
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256

import pytest

from pailie5.filter_fair_longitudinal_v3743 import run_longitudinal
from pailie5.filter_conflict_certificates_v3744 import (
    ALL_MASK, METHOD_COUNT, build_conflict_certificates,
)
from pailie5.filter_compatible_repairs_v3745 import (
    _solve_counts, build_repair_certificates, verify_repair_certificates,
)


def _certs_for_sets(sets):
    certs = []
    for mask in range(1, ALL_MASK + 1):
        chosen = [sets[i] for i in range(METHOD_COUNT)
                  if mask & (1 << i)]
        common = set.intersection(*chosen)
        bitmap = bytearray((100000 + 7) // 8)
        for value in common:
            n = int(value)
            bitmap[n // 8] |= 1 << (n % 8)
        certs.append({
            "subset_mask": mask,
            "retained_count": len(common),
            "candidate_bitmap_sha256": sha256(bitmap).hexdigest(),
        })
    return certs


def _expand(singletons):
    """Filler IDs unique to each method to give every method K=100."""
    result = []
    for i, subset in enumerate(singletons):
        filler = {f"{1000 + i * 100 + j:05d}"
                  for j in range(100 - len(subset))}
        result.append(set(subset) | filler)
    return result


def test_three_way_obstruction_has_exact_minimal_relaxation():
    sets = _expand([
        {"00001", "00002"}, {"00002", "00003"},
        {"00001", "00003"}, {"00001", "00002", "00003"},
        {"00001", "00002", "00003"},
        {"00001", "00002", "00003"},
    ])
    result = _solve_counts(_certs_for_sets(sets))
    assert result["max_compatible_methods"] == 5
    assert result["min_methods_relaxed"] == 1
    assert result["all_max_compatible_masks"] == [59, 61, 62]
    assert result["chosen_mask"] == 59
    assert result["chosen_retained_count"] == 1
    assert result["blocked_single_addition_masks"] == [63]
    assert result["chosen_bitmap_sha256"] == _certs_for_sets(sets)[58]["candidate_bitmap_sha256"]


def test_disjoint_six_sets_require_relaxing_five_methods():
    sets = _expand([{f"{i:05d}"} for i in range(6)])
    result = _solve_counts(_certs_for_sets(sets))
    assert result["max_compatible_methods"] == 1
    assert result["min_methods_relaxed"] == 5
    assert result["all_max_compatible_masks"] == [1, 2, 4, 8, 16, 32]
    assert result["chosen_mask"] == 1
    assert result["chosen_retained_count"] == 100


def test_rejects_incomplete_malformed_and_nonmonotone_lattice():
    sets = _expand([{f"{i:05d}"} for i in range(6)])
    base = _certs_for_sets(sets)
    for mutation in (
        lambda a: a.pop(),
        lambda a: a[3].update(subset_mask=3),
        lambda a: a[0].update(retained_count=True),
        lambda a: a[0].update(retained_count=99),
        lambda a: a[2].update(retained_count=101),
        lambda a: a[0].update(candidate_bitmap_sha256="X" * 64),
    ):
        bad = deepcopy(base)
        mutation(bad)
        with pytest.raises(ValueError):
            _solve_counts(bad)


@lru_cache(maxsize=2)
def _inputs():
    frozen = run_longitudinal(windows=4)
    conflicts = build_conflict_certificates(frozen)
    return frozen, conflicts


def test_four_windows_exact_oracle_replay_and_source_binding():
    frozen, conflicts = _inputs()
    result = build_repair_certificates(frozen, conflicts)
    verify_repair_certificates(frozen, conflicts, result)
    assert result == build_repair_certificates(frozen, conflicts)
    assert result["window_count"] == 4
    assert result["uses_observed_ids_to_choose_portfolio"] is False
    assert result["historical_coverage_verified"] is False
    for row, source in zip(result["windows"], frozen["records"]):
        sets = [set(m["candidate_ids"])
                for m in source["panel"]["payload"]["methods"]]
        masks = range(1, ALL_MASK + 1)
        counts = {m: len(set.intersection(
            *(sets[i] for i in range(METHOD_COUNT) if m & (1 << i))
        )) for m in masks}
        assert row["max_compatible_methods"] == max(
            m.bit_count() for m in masks if counts[m])
        assert counts[row["chosen_mask"]] == row["chosen_retained_count"]
        assert row["chosen_retained_count"] > 0
        assert all(counts[m] == 0 for m in row["blocked_single_addition_masks"])


def test_tampering_rejected_without_recomputing_any_missing_evidence():
    frozen, conflict = _inputs()
    result = build_repair_certificates(frozen, conflict)
    modifications = (
        lambda r: r["windows"][0].update(chosen_mask=63),
        lambda r: r["windows"][0].update(chosen_retained_count=0),
        lambda r: r["windows"][0]["all_max_compatible_masks"].clear(),
        lambda r: r["windows"].reverse(),
        lambda r: r["summary"].update(selected_retained_count_total=999),
        lambda r: r.update(conflict_report_sha256="0" * 64),
        lambda r: r.update(historical_coverage_verified=True),
    )
    for change in modifications:
        modified = deepcopy(result)
        change(modified)
        with pytest.raises(ValueError):
            verify_repair_certificates(frozen, conflict, modified)
    altered = deepcopy(conflict)
    altered["windows"][0]["subset_certificates"][0]["retained_count"] -= 1
    with pytest.raises(ValueError):
        verify_repair_certificates(frozen, altered, result)


def test_24_window_fixed_synthetic_contract():
    frozen = run_longitudinal(windows=24)
    conflicts = build_conflict_certificates(frozen)
    result = build_repair_certificates(frozen, conflicts)
    assert result["window_count"] == 24
    assert result["summary"]["all_six_incompatible_windows"] == 24
    assert sum(result["summary"]["max_compatible_method_count_histogram"].values()) == 24
    assert all(r["chosen_retained_count"] in range(1, 101)
               for r in result["windows"])
    verify_repair_certificates(frozen, conflicts, result)
