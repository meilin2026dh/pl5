"""Exact weighted scalar membership-probe order for frozen AND rules.

The input bitmaps and positive integer cost units are fixed before planning.
This is a bounded cost-model audit, not a wall-clock benchmark or a rule search.
"""
from fractions import Fraction
from hashlib import sha256

MAX_RULES = 12
MAX_DOMAIN = 100_000
MAX_COST = 10**9


def audit_weighted_order(masks, costs, *, universe_size=MAX_DOMAIN, hard_mask=None):
    """Minimize sum(cost[i] * survivors_before_i) over all permutations.

    Costs exclude bitmap construction, planning, materialization and caching.
    The hard mask is already applied; its cost is not part of the objective.
    Ties use lexicographically smallest rule-index permutation.
    """
    if type(universe_size) is not int or not 1 <= universe_size <= MAX_DOMAIN:
        raise ValueError("invalid universe size")
    masks, costs = tuple(masks), tuple(costs)
    m = len(masks)
    if not 1 <= m <= MAX_RULES or len(costs) != m:
        raise ValueError("expected 1..12 masks and matching costs")
    full = (1 << universe_size) - 1
    hard = full if hard_mask is None else hard_mask
    if any(type(x) is not int or not 0 <= x <= full for x in (hard, *masks)):
        raise ValueError("invalid bitmap")
    if any(type(c) is not int or not 1 <= c <= MAX_COST for c in costs):
        raise ValueError("costs must be positive bounded integers")

    total = 1 << m
    kept = [0] * total
    counts = [0] * total
    kept[0], counts[0] = hard, hard.bit_count()
    for s in range(1, total):
        bit = s & -s
        kept[s] = kept[s ^ bit] & masks[bit.bit_length() - 1]
        counts[s] = kept[s].bit_count()

    def solve(weights):
        best = [(0, ())] * total
        for s in range(1, total):
            choices = []
            remaining = s
            while remaining:
                bit = remaining & -remaining
                i = bit.bit_length() - 1
                parent = s ^ bit
                work, order = best[parent]
                choices.append((work + weights[i] * counts[parent], order + (i,)))
                remaining ^= bit
            best[s] = min(choices)
        return best[-1]

    def trace(order):
        state = 0
        work = 0
        stages = []
        for i in order:
            before = counts[state]
            state |= 1 << i
            charge = costs[i] * before
            stages.append({"rule_index": i, "probes": before,
                           "retained": counts[state], "weighted_cost": charge})
            work += charge
        return {"order": list(order), "weighted_cost": work,
                "scalar_probes": sum(s["probes"] for s in stages), "stages": stages}

    # Compare with the current cost-hint ordering, an exact equal-unit
    # ordering, and conditional greedy marginal exclusion per cost.
    left = list(range(m))
    state = 0
    greedy = []
    while left:
        i = min(left, key=lambda j: (
            -Fraction(counts[state] - counts[state | (1 << j)], costs[j]), j))
        left.remove(i)
        greedy.append(i)
        state |= 1 << i

    minimum, order = solve(costs)
    optimal = trace(order)
    baselines = {
        "cost_only": trace(sorted(range(m), key=lambda i: (costs[i], i))),
        "equal_unit_optimal": trace(solve((1,) * m)[1]),
        "greedy_exclusion_per_cost": trace(greedy),
    }
    if optimal["weighted_cost"] != minimum or any(
        p["weighted_cost"] < minimum for p in baselines.values()
    ):
        raise AssertionError("inconsistent weighted-order proof")
    width = (universe_size + 7) // 8
    digest = lambda bits: sha256(bits.to_bytes(width, "little")).hexdigest()
    return {
        "schema": "pl5-weighted-filter-order-v3746-1",
        "cost_model": "FIXED_INTEGER_COST_PER_SCALAR_MEMBERSHIP_PROBE",
        "universe_size": universe_size, "costs": list(costs),
        "hard_mask_sha256": digest(hard),
        "rule_mask_sha256": [digest(mask) for mask in masks],
        "subsets": total, "transitions_per_solve": m * (1 << (m - 1)),
        "retained": counts[-1], "final_mask_sha256": digest(kept[-1]),
        "optimal": optimal, "baselines": baselines,
        "historical_coverage_measured": False,
        "wall_clock_measured": False,
    }
