"""V3.7.38 linked exact auditors: independent candidate-mask conservation."""
import json

import pytest

from pailie5.digit_structure_v3737 import DOMAIN, RULES, compile_rule, reference_baseline
from pailie5.dsc_portfolio_audit_v3738 import run_dsc_portfolio_audit
from pailie5.ga_cs_optimizer_v3715 import SearchProblem, evaluate_genome


def _problem(cap):
    return SearchProblem(
        masks=tuple(compile_rule(x) for x in RULES),
        rule_names=tuple(x.name for x in RULES),
        universe_size=DOMAIN, target=cap, min_survivors=1,
        max_survivors=cap, min_active=0, hard_mask=reference_baseline(),
    )


def test_all_subsets_counted_without_quota_repair_and_reports_consistent():
    data = run_dsc_portfolio_audit(max_candidates=100)
    assert data == run_dsc_portfolio_audit(max_candidates=100)
    assert data["exact_portfolio_subsets"] == 32
    assert data["rule_count"] == len(RULES) == 5
    assert sum(row["ordered_incremental_excluded"] for row in data["structural_rule_metrics"]) == data["dsc_incremental_excluded"]
    assert data["baseline_keep_count"] - data["dsc_incremental_excluded"] == data["all_dsc_keep_count"]
    assert data["full_bitmap_equivalence_proven"]
    assert data["minimum_equivalent_rule_count"] <= len(RULES) - 1
    assert data["structural_rule_metrics"][-1]["ordered_zero_marginal"]
    assert data["historical_labels_read"] is False
    assert data["historical_coverage_measured"] is False
    assert json.loads(json.dumps(data)) == data
    p = _problem(100)
    feasible = [evaluate_genome(p, bits) for bits in range(32)]
    feasible = [x for x in feasible if x.feasible]
    assert data["exact_feasible_subsets"] == len(feasible)
    if data["best_under_cap"] is None:
        assert not feasible and data["best_mask_sha256"] is None
    else:
        b = data["best_under_cap"]
        assert b["survivor_count"] <= 100
        assert b["genome"] in {x.genome for x in feasible}


def test_uncapped_structural_audit_has_exactly_same_full_bitmap():
    a = run_dsc_portfolio_audit(max_candidates=100)
    b = run_dsc_portfolio_audit(max_candidates=DOMAIN)
    assert a["all_dsc_keep_sha256"] == b["all_dsc_keep_sha256"]
    assert a["baseline_keep_sha256"] == b["baseline_keep_sha256"]
    assert a["dsc_incremental_excluded"] == b["dsc_incremental_excluded"]
    assert b["exact_feasible_subsets"] >= a["exact_feasible_subsets"]
    assert b["best_under_cap"] is not None
    assert b["best_under_cap"]["survivor_count"] >= 1


def test_existing_frozen_baseline_and_duplicate_control_do_not_create_new_ids():
    a = run_dsc_portfolio_audit(max_candidates=DOMAIN)
    s = a["structural_rule_metrics"]
    assert s[0]["standalone_excluded"] == 100
    assert s[1]["standalone_excluded"] == 100
    assert s[2]["standalone_excluded"] == 6400
    assert s[4]["standalone_excluded"] == s[0]["standalone_excluded"]
    assert s[4]["ordered_incremental_excluded"] == 0
    assert a["all_dsc_keep_count"] <= a["baseline_keep_count"]


@pytest.mark.parametrize("bad", [0, -1, True, 100001, 1.5, "100"])
def test_bad_caps_fail_closed(bad):
    with pytest.raises(ValueError):
        run_dsc_portfolio_audit(max_candidates=bad)


def test_exact_frozen_100000_identity_negative_result_and_minimal_core():
    """Independent 32-subset census certifies failure of the 100-ID budget."""
    from fractions import Fraction
    report = run_dsc_portfolio_audit(max_candidates=100)
    assert report["baseline_keep_count"] == 94890
    assert report["all_dsc_keep_count"] == 87404
    assert report["dsc_incremental_excluded"] == 7486
    assert report["exact_portfolio_subsets"] == 32
    assert report["exact_feasible_subsets"] == 0
    assert report["best_under_cap"] is None
    assert report["cap_infeasibility_certificate"] == {
        "full_inventory_is_subset_minimum": True,
        "minimum_retained_exact": 87404,
        "target_upper_bound": 100,
        "mathematically_infeasible": True,
        "subsets_enumerated": 32,
    }
    assert report["minimum_equivalent_genome"] == 0b01100
    assert report["minimum_equivalent_rule_count"] == 2
    assert report["equivalent_pruned_rules"] == [
        "exclude_low_delta_diversity", "exclude_near_period2"
    ]
    assert report["scalar_checks_saved_by_equivalent_pruning"] > 0
    assert [x["ordered_incremental_excluded"] for x in report["structural_rule_metrics"]] == [
        90, 40, 5728, 1628, 0
    ]
    # Exact Shapley credits need not be zero for a rule added last with
    # zero sequential marginal; sharing of overlapping exclusions matters.
    shares = report["structural_rule_metrics"]
    assert Fraction(shares[-1]["shapley_excluded_numerator"],
                    shares[-1]["shapley_excluded_denominator"]) > 0
    exact_sum = sum((
        Fraction(r["shapley_excluded_numerator"], r["shapley_excluded_denominator"])
        for r in shares
    ), Fraction(0))
    assert exact_sum == 7486

    masks = tuple(compile_rule(x) for x in RULES)
    hard = reference_baseline()
    final = hard
    for mask in masks:
        final &= mask
    full_counts = []
    equivalent_masks = []
    for subset in range(1 << len(masks)):
        keep = hard
        for i, bitset in enumerate(masks):
            if subset & (1 << i):
                keep &= bitset
        full_counts.append(keep.bit_count())
        if keep == final:
            equivalent_masks.append(subset)
    assert min(full_counts) == 87404
    assert all(n > 100 for n in full_counts)
    assert len(equivalent_masks) == 8
    assert min(equivalent_masks, key=lambda k: (k.bit_count(), k)) == 0b01100


def test_full_domain_cap_is_not_mistaken_for_100_id_compression():
    report = run_dsc_portfolio_audit(max_candidates=DOMAIN)
    cert = report["cap_infeasibility_certificate"]
    assert cert["target_upper_bound"] == DOMAIN
    assert cert["minimum_retained_exact"] == 87404
    assert cert["mathematically_infeasible"] is False
