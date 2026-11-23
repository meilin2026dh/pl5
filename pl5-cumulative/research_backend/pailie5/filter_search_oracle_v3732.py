"""V3.7.32 bounded filter-combination search versus exact same-objective oracle.

This work package evaluates optimization/search efficiency ONLY, with a fixed
frozen inventory of Boolean keep masks. Neither fit, scoring nor metrics use
historical winning numbers, hidden labels, or future outcomes.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from .constraint_portfolio_v3731 import MAX_EXHAUSTIVE_RULES
from .ga_cs_optimizer_v3715 import SearchProblem, Candidate, evaluate_genome, optimize

SCHEMA = "pl5-filter-optimizer-oracle-v3732-1"
METHODS = ("random", "ga_cs")


def _canonical_hash(payload: object) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _problem_manifest(p: SearchProblem) -> dict[str, Any]:
    size = (p.universe_size + 7) // 8
    return {
        "universe_size": p.universe_size,
        "target": p.target,
        "min_survivors": p.min_survivors,
        "max_survivors": p.max_survivors,
        "min_active": p.min_active,
        "complexity_weight": p.complexity_weight,
        "hard_mask_sha256": (sha256(p.hard_mask.to_bytes(size, "little")).hexdigest()
                             if p.hard_mask is not None else None),
        "rules": [{"name": name, "sha256": sha256(mask.to_bytes(
            size, "little")).hexdigest()} for name, mask in zip(p.rule_names, p.masks)],
    }


def _key(c: Candidate) -> tuple[float, float, int]:
    """Reproduce optimizer's exact fitness ordering incl. deterministic ties."""
    return float(c.feasible), c.fitness, -c.genome


def compare_search_to_exact_oracle(
    problem: SearchProblem, *, seeds: tuple[int, ...] = (373201, 373202, 373203),
    evaluations: int = 48, switch_ratio: float = 0.3,
) -> dict[str, Any]:
    """Enumerate true GA-CS objective optimum and run equally charged searches.

    Compare GA-CS and random over *identical candidate-evaluation budgets*.
    Exhaustive oracle's 2^m evaluations are separately charged; no comparison
    calls the oracle at the same time-budget. Each seed is paired between arms.
    """
    if not isinstance(problem, SearchProblem):
        raise ValueError("validated SearchProblem required")
    m = len(problem.masks)
    if m > MAX_EXHAUSTIVE_RULES or problem.universe_size > 100_000:
        raise ValueError("exhaustive oracle exceeds declared limit")
    if (type(evaluations) is not int or evaluations < 1
            or not isinstance(seeds, tuple) or not seeds
            or any(type(s) is not int or s < 0 for s in seeds)
            or len(set(seeds)) != len(seeds)
            or type(switch_ratio) not in (int, float)
            or not 0 < switch_ratio < 1):
        raise ValueError("bad seed/budget/switch protocol")
    manifest = _problem_manifest(problem)
    if not all(type(mask) is int for mask in problem.masks):
        raise ValueError("invalid masks")

    oracle = max((evaluate_genome(problem, genome) for genome in range(1 << m)),
                 key=_key)
    trials = []
    for seed in seeds:
        row = {"seed": seed, "arms": {}}
        for method in METHODS:
            trial = optimize(problem, method=method, evaluations=evaluations,
                             seed=seed, switch_ratio=switch_ratio)
            if trial.evaluations != evaluations or len(trial.best_trace) != evaluations:
                raise ValueError("optimizer did not account for all evaluations")
            if sum(trial.stage_evaluations.values()) != evaluations:
                raise ValueError("optimizer stage accounting mismatch")
            if trial.best != evaluate_genome(problem, trial.best.genome):
                raise ValueError("optimizer supplied inconsistent result")
            if _key(trial.best) > _key(oracle):
                raise ValueError("optimizer beats exhaustive oracle; audit broken")
            row["arms"][method] = {
                "best_genome": trial.best.genome,
                "survivors": trial.best.survivors,
                "rule_count": trial.best.rule_count,
                "feasible": trial.best.feasible,
                "fitness": trial.best.fitness,
                "exact_objective_optimum_reached": trial.best == oracle,
                "fitness_gap": round(oracle.fitness - trial.best.fitness, 12)
                    if trial.best.feasible == oracle.feasible else None,
                "stage_evaluations": trial.stage_evaluations,
                "evaluations": trial.evaluations,
            }
        trials.append(row)
    return {
        "schema": SCHEMA, "rule_inventory": manifest,
        "inventory_sha256": _canonical_hash(manifest),
        "evaluation_budget_per_arm": evaluations,
        "method_order": list(METHODS),
        "seed_schedule": list(seeds),
        "ga_cs_switch_ratio": switch_ratio,
        "oracle": {
            "evaluations": 1 << m, "best_genome": oracle.genome,
            "survivors": oracle.survivors, "feasible": oracle.feasible,
            "fitness": oracle.fitness, "rule_count": oracle.rule_count,
        },
        "trials": trials,
        "summary": {
            method: {
                "trials": len(trials),
                "exact_optimum_reached": sum(int(row["arms"][method][
                    "exact_objective_optimum_reached"]) for row in trials),
                "feasible": sum(int(row["arms"][method]["feasible"]) for row in trials),
            } for method in METHODS
        },
        "evidence": "INTERNAL_FROZEN_MASK_OPTIMIZATION_ONLY",
        "historical_coverage_measured": False,
        "forecasting_performed": False,
        "future_advantage_claim": False,
        "warnings": [
            "This audit uses only static masks, not draw outcomes; it measures optimization objective attainment, not historical containment.",
            "GA-CS and random have equal objective-evaluation counts, but not equal wall-clock or energy costs.",
            "The exact oracle uses 2^m distinct evaluations, not the restricted search budget.",
            "The oracle and search algorithms are compared using GA-CS's SAME preexisting scalar fitness; the V3.7.31 three-objective Pareto frontier is a distinct objective.",
            "The best result across several seeds cannot be described as an unbiased single-trial outcome; all seeds are disclosed.",
        ],
    }
