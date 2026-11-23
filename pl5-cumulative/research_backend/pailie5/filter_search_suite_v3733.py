"""V3.7.33: preregistered synthetic filter-portfolio optimizer comparison.

No draw history, outcome labels or private source data. Frozen inventories
test whether GA-CS finds an existing *engineering* objective optimum faster
in objective evaluations than equally budgeted random portfolio search.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from .ga_cs_optimizer_v3715 import SearchProblem
from .filter_search_oracle_v3732 import compare_search_to_exact_oracle

VERSION = "pl5-filter-search-suite-v3733-1"
FAMILIES = ("nested", "orthogonal", "redundant", "conflicting")
SEEDS = (373301, 373302, 373303, 373304, 373305)
EVALUATIONS = 32
DOMAIN = 4096


def make_inventory(family: str) -> SearchProblem:
    """Eight deterministic, developer-authored keep masks on 4096 IDs."""
    if family not in FAMILIES:
        raise ValueError("unknown synthetic family")
    full = (1 << DOMAIN) - 1
    if family == "nested":
        # Includes portfolios that meet the strict 1..128 survivor interval.
        limits = (3000, 2200, 1600, 1100, 750, 450, 250, 100)
        masks = tuple((1 << bound) - 1 for bound in limits)
    elif family == "orthogonal":
        masks = tuple(sum(1 << i for i in range(DOMAIN)
                          if (i // (2 ** j)) % 2 == 0) for j in range(8))
    elif family == "redundant":
        a = sum(1 << i for i in range(DOMAIN) if i % 2 == 0)
        b = sum(1 << i for i in range(DOMAIN) if i % 3 == 0)
        c = sum(1 << i for i in range(DOMAIN) if i % 5 == 0)
        d = sum(1 << i for i in range(DOMAIN) if i % 7 == 0)
        masks = (a, b, a, b, c, c, d, full)
    else:
        # Intentional empty intersections: fail to attain constraints rather
        # than pretend that hard conflicts can be repaired after selection.
        a = sum(1 << i for i in range(DOMAIN) if i < DOMAIN // 2)
        b = full ^ a
        c = sum(1 << i for i in range(DOMAIN) if i % 5 == 0)
        d = sum(1 << i for i in range(DOMAIN) if i % 7 == 0)
        masks = (a, b, c, d, a, b, full, full)
    return SearchProblem(
        masks=masks, rule_names=tuple(f"{family}_{i}" for i in range(8)),
        universe_size=DOMAIN, target=64, min_survivors=1,
        max_survivors=128, min_active=1,
    )


def run_benchmark(*, seeds: tuple[int, ...] = SEEDS,
                  evaluations: int = EVALUATIONS) -> dict:
    """Fixed suite and seed schedule; disclose every negative trial."""
    if (not isinstance(seeds, tuple) or not seeds
            or len(set(seeds)) != len(seeds)
            or any(type(s) is not int or s < 0 for s in seeds)
            or type(evaluations) is not int or not 1 <= evaluations <= 1024):
        raise ValueError("invalid fixed research budget")
    studies = []
    for family in FAMILIES:
        comparison = compare_search_to_exact_oracle(
            make_inventory(family), seeds=seeds, evaluations=evaluations
        )
        studies.append({"family": family, "comparison": comparison})
    all_trials = [trial for study in studies for trial in study["comparison"]["trials"]]
    paired = {
        "ga_cs_only_exact_optimum": 0,
        "random_only_exact_optimum": 0,
        "both_exact_optimum": 0,
        "neither_exact_optimum": 0,
    }
    for trial in all_trials:
        ga = trial["arms"]["ga_cs"]["exact_objective_optimum_reached"]
        random = trial["arms"]["random"]["exact_objective_optimum_reached"]
        if ga and random:
            paired["both_exact_optimum"] += 1
        elif ga:
            paired["ga_cs_only_exact_optimum"] += 1
        elif random:
            paired["random_only_exact_optimum"] += 1
        else:
            paired["neither_exact_optimum"] += 1
    input_hashes = {study["family"]: study["comparison"]["inventory_sha256"]
                    for study in studies}
    return {
        "schema": VERSION,
        "fixtures": "INTERNAL_DEVELOPER_AUTHORED_ONLY",
        "family_order": list(FAMILIES), "seeds": list(seeds),
        "candidate_evaluations_per_arm_and_trial": evaluations,
        "total_trials": len(all_trials),
        "oracle_evaluations_per_family": 1 << 8,
        "input_inventory_hashes": input_hashes,
        "paired_exact_optimum_table": paired,
        "summary_by_family": {
            study["family"]: study["comparison"]["summary"] for study in studies
        },
        "full_studies": studies,
        "forecasting_performed": False,
        "historical_outcomes_read": False,
        "historical_coverage_measured": False,
        "predictive_advantage_claim": False,
        "algorithm_superiority_claim": False,
        "limits": [
            "Synthetic deterministic rule families are not representative real data.",
            "Different search algorithms have matched objective evaluation counts, not equal CPU time or power.",
            "Full synthetic suite and all seeds are disclosed; no after-the-fact family exclusion is allowed.",
            "Searching other hyperparameters on the same suite makes it a development set, not an independent comparison.",
            "This module never evaluates historical lottery outcomes or future prediction.",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Internal fixed-mask optimizer audit")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = run_benchmark()
    output = args.output
    if output.exists():
        raise FileExistsError("refuse to overwrite existing evidence")
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(result, ensure_ascii=False, sort_keys=True,
                         indent=2, allow_nan=False) + "\n"
    output.write_text(encoded, encoding="utf-8")
    print(json.dumps({"output": str(output), "sha256": sha256(encoded.encode()).hexdigest(),
                      "trials": result["total_trials"],
                      "paired_exact_optimum_table": result["paired_exact_optimum_table"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
