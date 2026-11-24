"""V3.7.39: exact affine recurrence filter grammar on five decimal digits.

Research object: deterministic Boolean constraints on the finite 100000-ID
domain, not a test on a short observed bitstream. Three independent modular
recurrence conditions define 100 identities by construction. This is a
compression *capacity* certificate; it is not evidence of historical
retention or general usefulness.
"""
from __future__ import annotations

from hashlib import sha256

import numpy as np

from .digit_structure_v3737 import DOMAIN, _bits, _hash, reference_baseline
from .engine import DIGITS
from .ga_cs_optimizer_v3715 import SearchProblem
from .constraint_portfolio_v3731 import exact_filter_portfolio
from .filter_interactions_v3734 import audit_filter_interactions

SCHEMA = "pl5-affine-recurrence-filter-v3739-1"
RULE_NAMES = (
    "recurrence_d2_eq_d0_plus_d1_mod10",
    "recurrence_d3_eq_d1_plus_d2_mod10",
    "recurrence_d4_eq_d2_plus_d3_mod10",
)


def recurrence_keep_masks() -> tuple[int, int, int]:
    """Three local independent equations; each constraint keeps 10% of U."""
    a = np.asarray(DIGITS, dtype=np.int16)
    if a.shape != (DOMAIN, 5):
        raise ValueError("unexpected candidate identity domain")
    return tuple(_bits((a[:, i + 2] - a[:, i] - a[:, i + 1]) % 10 == 0)
                 for i in range(3))


def audit_recurrence_filters() -> dict:
    """Exact structural enumeration and matched-cap subset comparison."""
    masks = recurrence_keep_masks()
    full = (1 << DOMAIN) - 1
    survivor = full
    stages = []
    for name, mask in zip(RULE_NAMES, masks):
        before = survivor.bit_count()
        survivor &= mask
        stages.append({
            "rule": name,
            "standalone_keep": mask.bit_count(),
            "before": before,
            "after": survivor.bit_count(),
            "additional_exclusions": before - survivor.bit_count(),
            "mask_sha256": _hash(mask),
        })
    if [x["after"] for x in stages] != [10000, 1000, 100]:
        raise AssertionError("modular recurrence sequence drifted")
    if survivor.bit_count() != 100:
        raise AssertionError("full recurrence space cardinality must equal 100")

    # Independent constructive oracle: choose d0,d1 freely; recursively
    # determine d2,d3,d4; identity must be a member of the full mask.
    constructed = set()
    for a in range(10):
        for b in range(10):
            digits = [a, b]
            for _ in range(3):
                digits.append((digits[-1] + digits[-2]) % 10)
            value = sum(digit * 10 ** (4 - i) for i, digit in enumerate(digits))
            constructed.add(value)
    if len(constructed) != 100 or any(not (survivor >> n) & 1 for n in constructed):
        raise AssertionError("constructive recurrence certificate failed")

    problem = SearchProblem(
        masks=masks, rule_names=RULE_NAMES, universe_size=DOMAIN,
        target=100, min_survivors=1, max_survivors=100, min_active=0,
    )
    portfolio = exact_filter_portfolio(problem)
    interaction = audit_filter_interactions(problem)
    if (portfolio["best"] is None or portfolio["best"]["genome"] != 7
            or portfolio["best"]["survivor_count"] != 100
            or interaction["all_rules_survivors"] != 100):
        raise AssertionError("independent portfolio engine disagrees")

    baseline = reference_baseline()
    baseline_and_new = baseline & survivor
    return {
        "schema": SCHEMA,
        "domain": DOMAIN,
        "rule_names": list(RULE_NAMES),
        "number_of_free_digits": 2,
        "constructive_enumeration_count": len(constructed),
        "stage_counts": stages,
        "full_mask_sha256": _hash(survivor),
        "exact_100_id_cap_feasible": True,
        "exact_subsets_checked": portfolio["subset_count"],
        "full_rule_interaction_shapley": interaction["shapley"],
        "baseline_keep_count": baseline.bit_count(),
        "baseline_intersection_count": baseline_and_new.bit_count(),
        "baseline_overlap_excluded_count": 100 - baseline_and_new.bit_count(),
        "baseline_intersection_sha256": _hash(baseline_and_new),
        "historical_data_read": False,
        "historical_coverage_measured": False,
        "structural_compression_by_construction": True,
        "algorithm_value_vs_existing_inventory_established": False,
        "limitations": [
            "The recurrence is an arbitrary predeclared modular grammar; meeting a size target does not establish greater rule quality.",
            "All three equations are full-domain constraints; examples are internal mathematical fixtures.",
            "Historical containment, rule-generation search complexity and practical runtime are not measured.",
            "Distinct full-domain 100-ID filter families can all satisfy the target while keeping different IDs.",
        ],
    }
