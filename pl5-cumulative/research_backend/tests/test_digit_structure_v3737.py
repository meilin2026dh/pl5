"""V3.7.37 exact structural feature and incremental exclusion falsification."""
from dataclasses import replace

import numpy as np
import pytest

from pailie5.digit_structure_v3737 import (
    DOMAIN, RULES, StructuralRule, _bits, audit_structural_increment,
    compile_rule, feature_table, reference_baseline,
)


def _membership(mask, ticket):
    return bool((mask >> int(ticket)) & 1)


def test_deterministic_feature_oracles_for_full_domain():
    f = feature_table()
    assert set(f) == {
        "mod10_curvature_zeros", "mod10_delta_distinct", "lag2_matches"
    }
    assert all(v.shape == (DOMAIN,) and not v.flags.writeable
               for v in f.values())
    for number, expected in {
        "12345": (3, 1, 0),
        "13579": (3, 1, 0),
        "24680": (3, 1, 0),
        "11111": (3, 1, 3),
        "12121": (0, 2, 3),
    }.items():
        i = int(number)
        assert tuple(int(f[k][i]) for k in (
            "mod10_curvature_zeros", "mod10_delta_distinct",
            "lag2_matches"
        )) == expected
    assert sum(int(v) for v in np.bincount(f["mod10_delta_distinct"])) == DOMAIN
    assert len({int(x) for x in f["mod10_delta_distinct"]}) == 4


def test_full_domain_exact_counts_and_nontrivial_overlap():
    full = (1 << DOMAIN) - 1
    ap = compile_rule(RULES[0])
    p2 = compile_rule(RULES[1])
    few = compile_rule(RULES[2])
    assert full.bit_count() == DOMAIN
    assert (full ^ ap).bit_count() == 100
    assert (full ^ p2).bit_count() == 100
    assert ((full ^ ap) & (full ^ p2)).bit_count() == 10
    assert (full ^ few).bit_count() == 6400
    assert not _membership(ap, "13579")
    assert not _membership(ap, "24680")
    assert not _membership(p2, "12121")
    assert _membership(ap, "12121")
    assert compile_rule(RULES[4]) == ap  # declared negative/duplicate control


def test_reference_baseline_and_exact_increment_conservation():
    base = reference_baseline()
    result = audit_structural_increment(base)
    assert 0 < result["final_keep_count"] <= result["baseline_count"] <= DOMAIN
    assert sum(row["additional_excluded_in_sequence"] for row in result["rule_metrics"]) == (
        result["baseline_count"] - result["final_keep_count"]
    )
    assert result == audit_structural_increment(base)
    assert result["rule_order"] == [r.name for r in RULES]
    assert result["rule_metrics"][-1]["zero_marginal_in_sequence"]
    assert result["rule_metrics"][0]["standalone_excluded"] == 100
    assert result["rule_metrics"][1]["standalone_excluded"] == 100
    assert result["rule_metrics"][2]["standalone_excluded"] == 6400
    assert all(0 <= row["additional_excluded_against_baseline"]
               <= row["standalone_excluded"] for row in result["rule_metrics"])
    assert result["historical_coverage_measured"] is False
    assert result["historical_labels_read"] is False


def test_order_changes_marginal_accounting_not_final_bitmap():
    full = (1 << DOMAIN) - 1
    base = audit_structural_increment(full, (RULES[0], RULES[1]))
    flipped = audit_structural_increment(full, (RULES[1], RULES[0]))
    assert base["final_keep_sha256"] == flipped["final_keep_sha256"]
    assert base["final_keep_count"] == flipped["final_keep_count"] == DOMAIN - 190
    assert [r["additional_excluded_in_sequence"] for r in base["rule_metrics"]] == [100, 90]
    assert [r["additional_excluded_in_sequence"] for r in flipped["rule_metrics"]] == [100, 90]


def test_empty_baseline_or_total_mask_still_has_correct_bounds():
    empty = audit_structural_increment(0, RULES[:1])
    assert empty["baseline_count"] == empty["final_keep_count"] == 0
    assert empty["rule_metrics"][0]["additional_excluded_in_sequence"] == 0
    full = audit_structural_increment((1 << DOMAIN) - 1, RULES[:1])
    assert full["incrementally_removed"] == 100


@pytest.mark.parametrize("rule", [
    StructuralRule("bad", "mod10_curvature_zeros", "ge", 100),
])
def test_valid_but_trivial_rule_is_accounted_not_invented(rule):
    result = audit_structural_increment((1 << DOMAIN) - 1, (rule,))
    assert result["final_keep_count"] == DOMAIN
    assert result["incrementally_removed"] == 0


@pytest.mark.parametrize("name,feature,operator,threshold", [
    ("", "mod10_curvature_zeros", "eq", 3),
    ("x", "unregistered", "eq", 3),
    ("x", "lag2_matches", "bad", 3),
    ("x", "lag2_matches", "eq", True),
])
def test_invalid_feature_definitions_fail_closed(name, feature, operator, threshold):
    with pytest.raises(ValueError):
        StructuralRule(name, feature, operator, threshold)


@pytest.mark.parametrize("invalid", [-1, 1 << DOMAIN, True, 3.5])
def test_invalid_baseline_masks_fail_closed(invalid):
    with pytest.raises(ValueError):
        audit_structural_increment(invalid)


def test_duplicate_names_and_mutable_rule_inputs_rejected():
    full = (1 << DOMAIN) - 1
    with pytest.raises(ValueError):
        audit_structural_increment(full, (RULES[0], replace(RULES[0], threshold=2)))
    with pytest.raises(ValueError):
        audit_structural_increment(full, [RULES[0]])
    with pytest.raises(ValueError):
        audit_structural_increment(full, tuple())
    with pytest.raises(ValueError):
        audit_structural_increment(full, tuple(RULES[:1]) * 13)
