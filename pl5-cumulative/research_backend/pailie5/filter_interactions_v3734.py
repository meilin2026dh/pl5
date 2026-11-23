"""V3.7.34 exact structural interaction audit for frozen Boolean KEEP masks.

No outcome data enter the audit. For static AND filters, the number excluded
is the cardinality of the union of rule-excluded sets: a monotone submodular
coverage function. Any apparent *positive extra* exclusion synergy is therefore
mathematically impossible; rules may overlap, not create new exclusions.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import math

from .ga_cs_optimizer_v3715 import SearchProblem
from .constraint_portfolio_v3731 import MAX_EXHAUSTIVE_RULES

SCHEMA = "pl5-static-filter-interactions-v3734-1"


def audit_filter_interactions(problem: SearchProblem) -> dict:
    """Bounded exact Shapley and overlap attribution for a frozen rule set.

    Contributions describe exclusions only; they do not measure historical
    outcome containment, future usefulness, or running time. The hard mask
    defines the starting population and is never assigned to optional rules.
    """
    if not isinstance(problem, SearchProblem):
        raise ValueError("validated SearchProblem required")
    m = len(problem.masks)
    if m > MAX_EXHAUSTIVE_RULES or problem.universe_size > 100_000:
        raise ValueError("exact interaction census capped at twelve rules and 100000 identities")
    hard = ((1 << problem.universe_size) - 1
            if problem.hard_mask is None else problem.hard_mask)
    total = 1 << m
    kept = [0] * total
    count = [0] * total
    kept[0] = hard
    count[0] = hard.bit_count()
    for subset in range(1, total):
        bit = subset & -subset
        index = bit.bit_length() - 1
        kept[subset] = kept[subset ^ bit] & problem.masks[index]
        count[subset] = kept[subset].bit_count()
    excluded = [count[0] - n for n in count]
    single = [excluded[1 << i] for i in range(m)]
    pairs = []
    for i in range(m):
        for j in range(i + 1, m):
            a, b = 1 << i, 1 << j
            both = excluded[a | b]
            overlap = single[i] + single[j] - both
            if overlap < 0 or overlap > min(single[i], single[j]):
                raise AssertionError("coverage identity violated")
            union_denominator = both
            pairs.append({
                "left": problem.rule_names[i], "right": problem.rule_names[j],
                "left_excluded": single[i], "right_excluded": single[j],
                "both_excluded": both, "overlap_excluded": overlap,
                "new_exclusions_right_after_left": both - single[i],
                "new_exclusions_left_after_right": both - single[j],
                "excluded_jaccard": (
                    {"numerator": overlap, "denominator": union_denominator}
                    if union_denominator else {"numerator": 0, "denominator": 1}
                ),
                "exact_duplicate_exclusions": (single[i] == single[j] == overlap),
            })

    # For every S and i,j outside S, the diminishing-returns gap is
    # f(S+i)+f(S+j)-f(S)-f(S+i+j), which must be >= 0.
    # This exact 2D face census is sufficient to prove submodularity.
    squares_checked = 0
    min_gap = None
    for subset in range(total):
        absent = (total - 1) ^ subset
        while absent:
            bit_i = absent & -absent
            rest = absent ^ bit_i
            while rest:
                bit_j = rest & -rest
                gap = (excluded[subset | bit_i] + excluded[subset | bit_j]
                       - excluded[subset] - excluded[subset | bit_i | bit_j])
                if gap < 0:
                    raise AssertionError("static conjunction violated submodularity")
                min_gap = gap if min_gap is None else min(min_gap, gap)
                squares_checked += 1
                rest ^= bit_j
            absent ^= bit_i

    # Exact Shapley partition of all excluded IDs. Avoid floating rounding.
    fact = [math.factorial(i) for i in range(m + 1)]
    denom = fact[m]
    shares = []
    for i, name in enumerate(problem.rule_names):
        bit = 1 << i
        numerator = 0
        for subset in range(total):
            if subset & bit:
                continue
            k = subset.bit_count()
            weight = fact[k] * fact[m - k - 1]
            numerator += weight * (excluded[subset | bit] - excluded[subset])
        value = Fraction(numerator, denom)
        shares.append({
            "rule": name, "solo_excluded": single[i],
            "shapley_excluded_numerator": value.numerator,
            "shapley_excluded_denominator": value.denominator,
            "zero_independent_contribution": value == 0,
        })
    exact_share_total = sum(
        (Fraction(row["shapley_excluded_numerator"],
                  row["shapley_excluded_denominator"]) for row in shares),
        Fraction(0),
    )
    if exact_share_total != excluded[-1]:
        raise AssertionError("exact Shapley conservation violated")

    # Bind the raw inventory (including hard mask, names, position) to digest.
    width = (problem.universe_size + 7) // 8
    manifest = sha256()
    manifest.update(f"v3734|{problem.universe_size}|{m}|".encode("ascii"))
    manifest.update(hard.to_bytes(width, "little"))
    for name, mask in zip(problem.rule_names, problem.masks):
        encoded = name.encode("utf8")
        manifest.update(len(encoded).to_bytes(4, "little"))
        manifest.update(encoded)
        manifest.update(mask.to_bytes(width, "little"))
    return {
        "schema": SCHEMA,
        "inventory_sha256": manifest.hexdigest(),
        "universe_size": problem.universe_size,
        "rule_count": m, "subsets_enumerated": total,
        "hard_mask_survivors": count[0],
        "all_rules_survivors": count[-1],
        "all_rules_excluded": excluded[-1],
        "singleton_excluded": dict(zip(problem.rule_names, single)),
        "pairwise": pairs, "pairs_checked": len(pairs),
        "submodularity_squares_checked": squares_checked,
        "minimum_diminishing_returns_gap": min_gap,
        "shapley": shares,
        "shapley_total_excluded_exact": excluded[-1],
        "static_and_monotone_submodular": True,
        "historical_outcomes_read": False,
        "historical_coverage_measured": False,
        "forecasting_performed": False,
        "future_advantage_claim": False,
        "interpretation": (
            "Static AND filters exclude a UNION of fixed excluded sets. "
            "They cannot have positive superadditive exclusion synergy. "
            "Overlapping exclusions make additional filters less effective "
            "after other filters, never more."
        ),
        "limits": [
            "The identity holds only for frozen static Boolean masks; conditional, time-varying or re-fitted rules require a separate model.",
            "Shapley values partition static excluded identities, not predictive merit, historical retained outcomes or causal importance.",
            "This is exact structural accounting, not a history-validity check or measured CPU performance.",
        ],
    }
