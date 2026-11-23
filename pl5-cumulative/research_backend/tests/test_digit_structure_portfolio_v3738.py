"""V3.7.38 exact frozen inventory integration and negative-result checks."""
from fractions import Fraction

from pailie5.constraint_portfolio_v3731 import exact_filter_portfolio
from pailie5.digit_structure_v3737 import DOMAIN, RULES, compile_rule, reference_baseline
from pailie5.digit_structure_portfolio_v3738 import (
    MAX_RETAINED, SCHEMA, audit_frozen_structural_portfolio,
)
from pailie5.ga_cs_optimizer_v3715 import SearchProblem


def test_snapshot_census_proves_budget_infeasibility_and_core_reduction():
    report = audit_frozen_structural_portfolio()
    assert report["schema"] == SCHEMA
    assert report["universe_size"] == 100_000
    assert report["inventory_size"] == 5
    assert report["subsets_enumerated"] == 32
    assert report["baseline_retained"] == 94890
    assert report["all_rules_retained"] == 87404
    assert report["all_rules_new_exclusions"] == 7486
    assert report["all_rules_retained_ratio"] == {"numerator": 87404, "denominator": 100000}
    assert report["target_retained_max"] == MAX_RETAINED == 100
    assert report["target_feasible"] is False
    assert report["constraint_portfolio_feasible_subsets"] == 0
    assert report["mathematical_infeasibility_certificate"] == {
        "full_inventory_is_subset_minimum": True,
        "minimum_retained_exact": 87404,
        "exceeds_target": True,
        "checked_subsets": 32,
    }
    assert report["exact_equivalence_core"]["genome"] == 0b01100
    assert report["exact_equivalence_core"]["rule_names"] == [
        "exclude_low_delta_diversity", "exclude_near_period2"
    ]
    assert report["exact_equivalence_core"]["rule_count"] == 2
    assert report["exact_equivalence_core"]["same_candidate_mask"] is True
    assert report["exact_equivalence_core"]["optional_scalar_checks_saved"] > 0
    assert [row["new_exclusions"] for row in report["ordered_marginals"]] == [
        90, 40, 5728, 1628, 0
    ]
    assert report["historical_data_read"] is False
    assert report["historical_recall_measured"] is False


def test_independent_bruteforce_subset_census_and_masks():
    hard = reference_baseline()
    keep = [compile_rule(rule) for rule in RULES]
    population = hard.bit_count()
    all_conjunction = hard
    for bitset in keep:
        all_conjunction &= bitset
    assert population == 94890
    assert all_conjunction.bit_count() == 87404

    equivalent = []
    counts = []
    for subset in range(1 << len(keep)):
        current = hard
        for i, bitset in enumerate(keep):
            if subset & (1 << i):
                current &= bitset
        counts.append(current.bit_count())
        if current == all_conjunction:
            equivalent.append(subset)
    assert min(counts) == all_conjunction.bit_count()
    assert len(counts) == 32
    assert len(equivalent) == 8
    assert min(equivalent, key=lambda subset: (subset.bit_count(), subset)) == 0b01100
    assert all(c > 100 for c in counts)


def test_exact_shapley_conservation_and_duplicate_attribution():
    report = audit_frozen_structural_portfolio()
    shares = report["shapley_exact"]
    assert len(shares) == 5
    value = sum((
        Fraction(row["shapley_excluded_numerator"], row["shapley_excluded_denominator"])
        for row in shares
    ), Fraction(0))
    assert value == report["all_rules_new_exclusions"] == 7486
    # Sequential zero-marginal does not imply Shapley zero under averaging.
    assert report["ordered_marginals"][-1]["new_exclusions"] == 0
    assert Fraction(
        shares[-1]["shapley_excluded_numerator"],
        shares[-1]["shapley_excluded_denominator"],
    ) > 0


def test_exact_portfolio_returns_no_fabricated_feasible_solution():
    p = SearchProblem(
        masks=tuple(compile_rule(rule) for rule in RULES),
        rule_names=tuple(rule.name for rule in RULES),
        universe_size=DOMAIN, target=100, min_survivors=1,
        max_survivors=100, hard_mask=reference_baseline(),
    )
    plan = exact_filter_portfolio(p)
    assert plan["subset_count"] == 32
    assert plan["best"] is None
    assert plan["best_mask_sha256"] is None
    assert plan["feasible_subset_count"] == 0


def test_repeatability_digest_and_report_structure():
    a = audit_frozen_structural_portfolio()
    b = audit_frozen_structural_portfolio()
    assert a == b
    assert len(a["baseline_keep_sha256"]) == 64
    assert len(a["all_rules_retained_sha256"]) == 64
    assert a["baseline_keep_sha256"] != a["all_rules_retained_sha256"]
    assert a["frozen_rule_names"] == [r.name for r in RULES]
