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
