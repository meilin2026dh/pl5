"""V3.7.31 — exact, history-blind Boolean filter-portfolio audit.

This is *filter engineering*, not a lottery prediction model. Enumerate bounded
AND combinations of an existing frozen SearchProblem inventory, calculate
their exact candidate count, prove the least scalar predicate-evaluation work
over all rule orders using subset DP, and report an exact 3D Pareto frontier.

No historical draws, labels or outcome data enter this module. For a uniform
independent target, any frozen K-element set has coverage K / universe_size.
This module cannot establish any future advantage.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any

from .ga_cs_optimizer_v3715 import SearchProblem

SCHEMA = "pl5-exact-constraint-portfolio-v3731-1"
MAX_EXHAUSTIVE_RULES = 12


@dataclass(frozen=True)
class Plan:
    genome: int
    survivor_count: int
    active_rule_count: int
    scalar_evaluation_cost: int
    optimal_rule_order: tuple[str, ...]
    target_distance: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _prepare(problem: SearchProblem, max_rules: int) -> tuple[list[int], list[int], list[int], list[tuple[int, ...]]]:
    if not isinstance(problem, SearchProblem):
        raise ValueError("expected a validated SearchProblem")
    if type(max_rules) is not int or not 1 <= max_rules <= MAX_EXHAUSTIVE_RULES:
        raise ValueError("max_rules must be integer in 1..12")
    m = len(problem.masks)
    if m > max_rules or problem.universe_size > 100_000:
        raise ValueError("exact planner capped at max_rules and PL5 universe size")
    total = 1 << m
    hard = (1 << problem.universe_size) - 1 if problem.hard_mask is None else problem.hard_mask
    # Each subset's final mask is computed from one smaller subset, so
    # EVERY possible AND combination is visited exactly once.
    kept = [hard] * total
    count = [hard.bit_count()] * total
    work = [0] * total
    order: list[tuple[int, ...]] = [()] * total
    for bits in range(1, total):
        last = bits & -bits
        idx = last.bit_length() - 1
        prev = bits ^ last
        kept[bits] = kept[prev] & problem.masks[idx]
        count[bits] = kept[bits].bit_count()

        # Exact Bellman recurrence. When rule i is evaluated LAST in bits,
        # prefix bits\{i} needs best work[bits\{i}], then exactly
        # count[bits\{i}] scalar predicate checks for rule i.
        choices = []
        remaining = bits
        while remaining:
            bit = remaining & -remaining
            i = bit.bit_length() - 1
            parent = bits ^ bit
            choices.append((work[parent] + count[parent], order[parent] + (i,)))
            remaining ^= bit
        work[bits], order[bits] = min(choices)
    return kept, count, work, order


def _frontier(rows: list[Plan], max_rules: int) -> list[Plan]:
    """Exact 3-objective minimization: target error, active rules, work.

    In ascending target-error order, any previous point with no more rules
    and no more work dominates. Equal objectives retain smallest genome.
    """
    prior_best_work = [float("inf")] * (max_rules + 1)
    frontier: list[Plan] = []
    for row in sorted(rows, key=lambda x: (
        x.target_distance, x.active_rule_count, x.scalar_evaluation_cost, x.genome
    )):
        if min(prior_best_work[:row.active_rule_count + 1]) <= row.scalar_evaluation_cost:
            continue
        frontier.append(row)
        prior_best_work[row.active_rule_count] = min(
            prior_best_work[row.active_rule_count], row.scalar_evaluation_cost
        )
    return frontier


def exact_filter_portfolio(problem: SearchProblem, *, max_rules: int = MAX_EXHAUSTIVE_RULES) -> dict[str, Any]:
    """Exact subset census and Pareto comparison against bounded GA-CS search.

    Feasibility follows SearchProblem's hard mask, minimum rule count, and
    min/max survivors. The target budget is used for *engineering* distance,
    never for historical hit optimization. If no feasible portfolio exists,
    fail closed: no fabricated quota-repair or synthetic candidate list.
    """
    kept, count, work, order = _prepare(problem, max_rules)
    m = len(problem.masks)
    total = 1 << m
    feasible: list[Plan] = []
    zero_survivor = 0
    for bits in range(total):
        n = count[bits]
        zero_survivor += int(n == 0)
        active = bits.bit_count()
        if active < problem.min_active or not problem.min_survivors <= n <= problem.max_survivors:
            continue
        feasible.append(Plan(
            genome=bits, survivor_count=n, active_rule_count=active,
            scalar_evaluation_cost=work[bits],
            optimal_rule_order=tuple(problem.rule_names[i] for i in order[bits]),
            target_distance=abs(n - problem.target),
        ))
    front = _frontier(feasible, m)
    # Choose one deterministic recommendation: closest to requested target;
    # then cheapest scalar work, then fewest active rules, then genome.
    best = min(feasible, key=lambda p: (
        p.target_distance, p.scalar_evaluation_cost, p.active_rule_count, p.genome
    )) if feasible else None
    diagnostics: list[dict[str, Any]] = []
    mask_sha256 = None
    if best:
        final_mask = kept[best.genome]
        byte_count = (problem.universe_size + 7) // 8
        mask_sha256 = sha256(final_mask.to_bytes(byte_count, "little")).hexdigest()
        # If deleting a rule recovers no candidate, that rule is redundant
        # for THIS portfolio, regardless of its standalone filtering power.
        for i, name in enumerate(problem.rule_names):
            if not best.genome & (1 << i):
                continue
            without = best.genome ^ (1 << i)
            diagnostics.append({
                "rule": name,
                "recoverable_if_removed": count[without] - best.survivor_count,
                "redundant_given_others": count[without] == best.survivor_count,
                "standalone_survivors_under_hard_mask": count[1 << i],
            })
    return {
        "schema": SCHEMA,
        "method": "EXACT_SUBSET_ENUMERATION_AND_BELLMAN_ORDER_DYNAMIC_PROGRAMMING",
        "rule_count": m,
        "subset_count": total,
        "feasible_subset_count": len(feasible),
        "empty_subset_count": zero_survivor,
        "hard_mask_survivors": count[0],
        "top_k_cap": problem.max_survivors,
        "target_survivors": problem.target,
        "min_survivors": problem.min_survivors,
        "min_active": problem.min_active,
        "frontier": [x.as_dict() for x in front],
        "frontier_count": len(front),
        "best": best.as_dict() if best else None,
        "best_mask_sha256": mask_sha256,
        "drop_one_diagnostics": diagnostics,
        "fair_uniform_coverage_of_best": (
            best.survivor_count / problem.universe_size if best else None
        ),
        "evidence": "EXACT_MASK_ENGINEERING_ONLY_NO_HISTORICAL_LABELS",
        "cost_unit": "scalar_candidate_predicate_evaluations",
        "cost_equal_to_wall_time": False,
        "historical_coverage_measured": False,
        "future_advantage_claim": False,
        "warnings": [
            "Results depend entirely on the provided static frozen bit masks and their provenance.",
            "Evaluation cost assumes scalar short-circuit checks; vectorized bitwise engines may have different wall time.",
            "No historical outcomes are read; neither retrospective nor future coverage is established.",
            "For iid-uniform draws, inclusion probability is exactly survivor_count/universe_size.",
            "The exhaustive Pareto proof covers only the provided inventory, not undiscovered filters or conditional compositions.",
        ],
    }
