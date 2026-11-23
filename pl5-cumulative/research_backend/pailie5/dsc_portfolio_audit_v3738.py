"""V3.7.38: auditable DSC-versus-baseline incremental filter portfolios.

This work package combines *existing* exact boolean search and interaction
auditors with the fixed V3.7.37 structure operators. It does not retune any
operator or change the underlying five-digit identity universe.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .digit_structure_v3737 import DOMAIN, RULES, audit_structural_increment, compile_rule, reference_baseline
from .ga_cs_optimizer_v3715 import SearchProblem
from .constraint_portfolio_v3731 import exact_filter_portfolio
from .filter_interactions_v3734 import audit_filter_interactions
from .filter_equivalent_pruning_v3735 import exact_equivalent_pruning

SCHEMA = "pl5-dsc-incremental-portfolio-v3738-1"


def run_dsc_portfolio_audit(*, max_candidates: int = 100) -> dict:
    """Audit all DSC combinations under a frozen conventional hard mask.

    The requested upper cap is a *constraint*, never silently repaired.
    The baseline and five DSC rules are frozen in the named V3.7.37 source.
    A feasible result is a filtering engineering result only.
    """
    if type(max_candidates) is not int or not 1 <= max_candidates <= DOMAIN:
        raise ValueError("candidate cap must be an integer within the universe")
    baseline = reference_baseline()
    kept = tuple(compile_rule(rule) for rule in RULES)
    problem = SearchProblem(
        masks=kept,
        rule_names=tuple(rule.name for rule in RULES),
        universe_size=DOMAIN,
        target=max_candidates,
        min_survivors=1,
        max_survivors=max_candidates,
        min_active=0,
        hard_mask=baseline,
    )
    sequential = audit_structural_increment(baseline)
    intersections = audit_filter_interactions(problem)
    exact = exact_filter_portfolio(problem)
    prune = exact_equivalent_pruning(problem)

    total = (1 << DOMAIN) - 1
    full_mask = baseline
    for mask in kept:
        full_mask &= mask
    final_sha = sha256(full_mask.to_bytes((DOMAIN + 7) // 8, "little")).hexdigest()

    # All linked auditors MUST agree, or fail closed. Zero-increment rules
    # are identified rather than assigned spurious marginal value.
    if (sequential["final_keep_count"] != full_mask.bit_count()
            or sequential["final_keep_sha256"] != final_sha
            or intersections["all_rules_survivors"] != full_mask.bit_count()
            or prune["all_rules_survivors"] != full_mask.bit_count()
            or prune["full_candidate_mask_sha256"] != final_sha
            or sum(row["additional_excluded_in_sequence"] for row in sequential["rule_metrics"])
                != baseline.bit_count() - full_mask.bit_count()):
        raise AssertionError("independent DSC auditing methods disagree")

    # The deliberately equivalent fifth operator must remain an explicit
    # control; exact pruning preserves the full candidate bitmap.
    if kept[0] != kept[4]:
        raise AssertionError("duplicate-control definition drift")
    if sequential["rule_metrics"][-1]["additional_excluded_in_sequence"] != 0:
        raise AssertionError("duplicate control unexpectedly gained new exclusions")

    rule_rows = []
    for i, rule in enumerate(RULES):
        metrics = sequential["rule_metrics"][i]
        interaction = intersections["shapley"][i]
        rule_rows.append({
            "name": rule.name,
            "feature": rule.feature, "operator": rule.operator,
            "threshold": rule.threshold,
            "standalone_excluded": metrics["standalone_excluded"],
            "new_excluded_against_baseline": metrics["additional_excluded_against_baseline"],
            "ordered_incremental_excluded": metrics["additional_excluded_in_sequence"],
            "ordered_zero_marginal": metrics["zero_marginal_in_sequence"],
            "shapley_excluded_numerator": interaction["shapley_excluded_numerator"],
            "shapley_excluded_denominator": interaction["shapley_excluded_denominator"],
        })

    return {
        "schema": SCHEMA,
        "frozen_hypotheses": "V3.7.37_PREDECLARED_STATIC_RULES",
        "universe_size": DOMAIN,
        "rule_count": len(RULES),
        "baseline_keep_count": baseline.bit_count(),
        "baseline_keep_sha256": sequential["baseline_keep_sha256"],
        "all_dsc_keep_count": full_mask.bit_count(),
        "all_dsc_keep_sha256": final_sha,
        "dsc_incremental_excluded": baseline.bit_count() - full_mask.bit_count(),
        "max_candidates": max_candidates,
        "exact_portfolio_subsets": exact["subset_count"],
        "exact_feasible_subsets": exact["feasible_subset_count"],
        "best_under_cap": exact["best"],
        "best_mask_sha256": exact["best_mask_sha256"],
        "pareto_frontier": exact["frontier"],
        "structural_rule_metrics": rule_rows,
        "pairwise_overlap": intersections["pairwise"],
        "minimum_equivalent_rule_count": prune["chosen_rule_count"],
        "equivalent_pruned_rules": prune["chosen_rule_names"],
        "removed_redundant_rules": prune["removed_rule_names"],
        "full_bitmap_equivalence_proven": prune["exact_bitmap_preserved"],
        "historical_coverage_measured": False,
        "historical_labels_read": False,
        "outcome_evidence_used_for_hypotheses": False,
        "limitations": [
            "All metrics are exact static bitmap arithmetic on a predeclared five-digit universe.",
            "The conventional sum/span baseline is illustrative, not calibrated against historical outcomes.",
            "A missing feasible <=cap subset remains None; no arbitrary fill, ranking, or quota repair.",
            "Shapley credits share overlapping exclusions; ordered marginal credits depend on rule order.",
            "Scalar predicate-evaluation cost is a proxy and does not establish a measured runtime gain.",
            "Historical containment must be evaluated separately on a frozen time-forward protocol.",
        ],
    }
