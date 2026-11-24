"""V3.7.35: exact subset-equivalent simplification of static filter inventories.

Find a minimum-rule AND portfolio that preserves the *entire* candidate
bitmap produced by every supplied rule (including the immutable hard mask).
This is deterministic static filter engineering; no outcome rows are read.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from .constraint_portfolio_v3731 import MAX_EXHAUSTIVE_RULES, _prepare
from .ga_cs_optimizer_v3715 import SearchProblem

SCHEMA = "pl5-exact-mask-equivalent-pruning-v3735-1"


def exact_equivalent_pruning(problem: SearchProblem) -> dict[str, Any]:
    """Minimize rule count, then exact scalar short-circuit work, then genome.

    The selected subset is proven equivalent to the conjunction of ALL masks
    on the entire hard-mask population, not merely similar in count or
    historically sampled records. No threshold repair or candidate restore.
    """
    if not isinstance(problem, SearchProblem):
        raise ValueError("validated SearchProblem required")
    if len(problem.masks) > MAX_EXHAUSTIVE_RULES or problem.universe_size > 100_000:
        raise ValueError("bounded exact pruning supports at most twelve rules / 100000 IDs")
    kept, count, work, orders = _prepare(problem, MAX_EXHAUSTIVE_RULES)
    m = len(problem.masks)
    all_genome = (1 << m) - 1
    target = kept[all_genome]
    exact_equivalents = [s for s in range(1 << m) if kept[s] == target]
    if not exact_equivalents:
        raise AssertionError("full set must be equivalent to itself")
    best = min(exact_equivalents, key=lambda s: (
        s.bit_count(), work[s], s
    ))
    # A valid minimal equivalent subset cannot contain a removable rule.
    for i in range(m):
        if best & (1 << i) and kept[best ^ (1 << i)] == target:
            raise AssertionError("nonminimal equivalent core")
    width = (problem.universe_size + 7) // 8
    fingerprint = sha256(target.to_bytes(width, "little")).hexdigest()
    # Distinguish rules essential in EVERY preserving subset from
    # dispensable-in-one-minimal-core rules. Alternative cores may exist.
    essential = [
        problem.rule_names[i] for i in range(m)
        if not any((subset & (1 << i)) == 0 for subset in exact_equivalents)
    ]
    cores = [s for s in exact_equivalents if all(
        kept[s ^ (1 << i)] != target
        for i in range(m) if s & (1 << i)
    )]
    return {
        "schema": SCHEMA,
        "all_rules_count": m,
        "subsets_examined": 1 << m,
        "exactly_equivalent_subset_count": len(exact_equivalents),
        "inclusion_minimal_core_count": len(cores),
        "all_rules_survivors": count[all_genome],
        "full_candidate_mask_sha256": fingerprint,
        "chosen_genome": best,
        "chosen_rule_count": best.bit_count(),
        "chosen_rule_names": [problem.rule_names[i] for i in range(m) if best & (1 << i)],
        "removed_rule_names": [problem.rule_names[i] for i in range(m) if not best & (1 << i)],
        "essential_across_all_equivalent_subsets": essential,
        "optimal_rule_order": [problem.rule_names[i] for i in orders[best]],
        "original_all_rules_minimum_scalar_checks": work[all_genome],
        "simplified_minimum_scalar_checks": work[best],
        "scalar_checks_saved": work[all_genome] - work[best],
        "exact_bitmap_preserved": True,
        "candidate_count_changed": False,
        "historical_outcomes_read": False,
        "historical_retention_measured": False,
        "limits": [
            "Exact equivalence is established only for frozen static masks and the specified hard-mask universe.",
            "Scalar predicate checks are a structural proxy, not measured elapsed time.",
            "Rule names and origins must be independently verified when applying this audit to external inventories.",
            "The smallest equivalent subset does not imply a better historical retention rate: candidate bitmap is identical.",
        ],
    }
