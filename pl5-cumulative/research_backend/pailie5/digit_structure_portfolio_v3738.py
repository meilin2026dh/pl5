"""V3.7.38: exact portfolio audit for the frozen V3.7.37 structural rules.

Bridge the structural operator inventory to existing exact Boolean portfolio,
interaction and equivalence-pruning engines. No additional operators, fitting,
historical records or changed threshold definitions are introduced.
"""
from __future__ import annotations

from .constraint_portfolio_v3731 import exact_filter_portfolio
from .digit_structure_v3737 import (
    DOMAIN, RULES, audit_structural_increment, compile_rule, reference_baseline,
)
from .filter_equivalent_pruning_v3735 import exact_equivalent_pruning
from .filter_interactions_v3734 import audit_filter_interactions
from .ga_cs_optimizer_v3715 import SearchProblem

SCHEMA = "pl5-structural-portfolio-bridge-v3738-1"
MAX_RETAINED = 100


def audit_frozen_structural_portfolio() -> dict:
    """Exhaustively compare all 2**5 subsets against a fixed reference mask.

    The baseline is an immutable hard constraint. All five structural rules
    are optional, including one deliberate duplicate. No candidate quota is
    repaired if an infeasible inventory is unable to reach the target.
    """
    baseline = reference_baseline()
    rules = RULES
    problem = SearchProblem(
        masks=tuple(compile_rule(r) for r in rules),
        rule_names=tuple(r.name for r in rules),
        universe_size=DOMAIN,
        target=MAX_RETAINED,
        min_survivors=1,
        max_survivors=MAX_RETAINED,
        min_active=0,
        hard_mask=baseline,
    )
    ordered = audit_structural_increment(baseline, rules)
    search = exact_filter_portfolio(problem)
    attribution = audit_filter_interactions(problem)
    pruning = exact_equivalent_pruning(problem)

    # Independent direct five-rule AND serves as a cross-engine certificate.
    direct = baseline
    for mask in problem.masks:
        direct &= mask
    least = direct.bit_count()
    if (search["hard_mask_survivors"] != baseline.bit_count()
            or ordered["final_keep_count"] != least
            or pruning["all_rules_survivors"] != least
            or attribution["all_rules_survivors"] != least
            or ordered["final_keep_sha256"] != pruning["full_candidate_mask_sha256"]
            or ordered["final_keep_sha256"] != search.get("best_mask_sha256")
            and search["best"] is not None):
        raise AssertionError("cross-engine candidate mask mismatch")
    if (ordered["incrementally_removed"]
            != attribution["all_rules_excluded"]
            or ordered["incrementally_removed"]
            != baseline.bit_count() - least):
        raise AssertionError("independent excluded-set accounting mismatch")

    # Under AND filters, the full inventory is the smallest possible
    # retained set among all subsets, regardless of rule execution order.
    impossible = least > MAX_RETAINED
    if impossible and (search["best"] is not None or search["feasible_subset_count"] != 0):
        raise AssertionError("infeasible candidate budget was incorrectly repaired")

    return {
        "schema": SCHEMA,
        "reference_baseline": "sum_10_to_35_AND_span_at_least_3",
        "universe_size": DOMAIN,
        "frozen_rule_names": list(problem.rule_names),
        "inventory_size": len(problem.masks),
        "subsets_enumerated": search["subset_count"],
        "baseline_keep_sha256": ordered["baseline_keep_sha256"],
        "baseline_retained": baseline.bit_count(),
        "all_rules_retained_sha256": ordered["final_keep_sha256"],
        "all_rules_retained": least,
        "all_rules_new_exclusions": ordered["incrementally_removed"],
        "all_rules_retained_ratio": {"numerator": least, "denominator": DOMAIN},
        "target_retained_max": MAX_RETAINED,
        "target_feasible": search["best"] is not None,
        "mathematical_infeasibility_certificate": {
            "full_inventory_is_subset_minimum": True,
            "minimum_retained_exact": least,
            "exceeds_target": impossible,
            "checked_subsets": search["subset_count"],
        },
        "exact_equivalence_core": {
            "rule_names": pruning["chosen_rule_names"],
            "rule_count": pruning["chosen_rule_count"],
            "genome": pruning["chosen_genome"],
            "same_candidate_mask": pruning["exact_bitmap_preserved"],
            "optional_scalar_checks_saved": pruning["scalar_checks_saved"],
        },
        "ordered_marginals": [
            {"rule": item["name"], "new_exclusions": item["additional_excluded_in_sequence"]}
            for item in ordered["rule_metrics"]
        ],
        "shapley_exact": attribution["shapley"],
        "shapley_total_excluded_exact": attribution["shapley_total_excluded_exact"],
        "constraint_portfolio_feasible_subsets": search["feasible_subset_count"],
        "historical_data_read": False,
        "historical_recall_measured": False,
        "cost_unit": "scalar_candidate_predicate_evaluations",
        "cost_is_wall_time": False,
        "limits": [
            "This fixed five-rule inventory cannot be extrapolated to unseen operator families.",
            "The reference baseline and rule list were frozen, not optimized on evaluation records.",
            "A 100-identity budget is an engineering constraint; none of the 32 subsets can reach it.",
            "Structural mask equivalence and scalar work are exactly enumerated, not empirical timing.",
            "The results contain no historical time-forward coverage measurement.",
        ],
    }
