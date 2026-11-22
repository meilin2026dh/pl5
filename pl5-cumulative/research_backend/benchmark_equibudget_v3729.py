"""Eight-task V3.7.29 *INTERNAL* equal-total-budget experiment.

All task formulae are public in benchmark_hard_budget_v3727.py and known to
the developer. 100 external unknown tasks remain unrun. This is an engineering
comparison under fixed 10s per model vs two independently capped 5s arms,
not proof of general mathematics discovery or lottery predictive skill.

Only a public, synthetic summary is exported. Secret Ed25519 test keys and
private answer labels remain in a temporary directory and are deleted.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from benchmark_hard_budget_v3727 import FAMILIES, SEEDS, task
from research_open_grammar_v3725 import prepare
from research_signed_blind_v3728 import keygen
from research_equibudget_v3729 import issue_pair, freeze_pair, settle_pair
from research_blind_protocol_v3729 import digest, _mcnemar

BACKEND = Path(__file__).resolve().parent
SEED = SEEDS[0]
ARMS = ("v3725_ring", "v3726_gate", "frozen_portfolio")


def run(out):
    out = Path(out)
    if out.exists():
        raise FileExistsError("do not overwrite frozen internal study output")
    rows = []
    for family in FAMILIES:
        # Developer-generated task. This does NOT establish independent
        # unknown-task provenance or a cryptographically trusted timing record.
        with tempfile.TemporaryDirectory(prefix="pl5-v3729-internal-") as temp:
            base = Path(temp)
            secrets = base / "private_secrets"
            secrets.mkdir()
            keys = {}
            for role in ("issuer", "solver", "grader"):
                keys[role] = (
                    secrets / f"{role}.key", base / f"{role}.pub")
                keygen(*keys[role])
            src = base / "internal_developer_task.json"
            src.write_text(json.dumps(task(family, SEED)), encoding="utf-8")
            prepare(src, base / "public", secrets / "holdout")
            public = base / "public" / "public_challenge.json"
            private = secrets / "holdout" / "private_challenge.json"
            issue_pair(public, BACKEND, *keys["issuer"], base / "issuer_attestations")
            freeze_pair(public, BACKEND, base / "issuer_attestations",
                        keys["issuer"][1], *keys["solver"], base / "solver")
            grades = settle_pair(public, private, BACKEND,
                                 base / "issuer_attestations",
                                 keys["issuer"][1], keys["solver"][1],
                                 *keys["grader"], base / "solver")
            telemetry = json.loads(
                (base / "solver" / "equal_budget_telemetry.json").read_text())
            for row in grades["rows"]:
                arm = row["arm"]
                completed = row["status"] == "EVALUATED"
                measurements = telemetry["arms"][arm]["observed_component_wall_ms"]
                rows.append({
                    "family": family,
                    "seed": SEED,
                    "task_id": row["task_id"],
                    "arm": arm,
                    "status": row["status"],
                    "holdout_errors": row["holdout_errors"],
                    "holdout_cells": row["holdout_cells"],
                    "budget_ms_total": row["budget_ms"],
                    "worker_actual_component_wall_ms_untrusted": measurements,
                    "exact_success": int(completed and row["holdout_errors"] == 0),
                    "external_blind_verified": False,
                })
    models = {}
    for arm in ARMS:
        entries = [r for r in rows if r["arm"] == arm]
        models[arm] = {
            "tasks": len(entries),
            "accepted": sum(r["status"] == "EVALUATED" for r in entries),
            "exact_success": sum(r["exact_success"] for r in entries),
            "rejected_timeout_failed": sum(r["status"] != "EVALUATED" for r in entries),
            "holdout_error_total": sum(r["holdout_errors"] or 0 for r in entries),
            "equal_total_budget_ms": 10000,
        }
    by_task = {(r["task_id"], r["arm"]): r["exact_success"] for r in rows}
    a = sum(by_task[(task(family, SEED)["task_id"], "frozen_portfolio")] == 1
            and by_task[(task(family, SEED)["task_id"], "v3726_gate")] == 0
            for family in FAMILIES)
    b = sum(by_task[(task(family, SEED)["task_id"], "frozen_portfolio")] == 0
            and by_task[(task(family, SEED)["task_id"], "v3726_gate")] == 1
            for family in FAMILIES)
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=BACKEND, text=True,
        capture_output=True, check=True).stdout.strip()
    summary = {
        "schema": "pl5-v3729-internal-eight-task-equal-total-budget-1",
        "git_commit": sha,
        "python": sys.version.split()[0],
        "platform": platform.system(),
        "task_families": list(FAMILIES),
        "seed": SEED,
        "tasks": len(FAMILIES),
        "method_rows": len(rows),
        "standalone_limit_ms": 10000,
        "portfolio_component_limit_ms": 5000,
        "portfolio_total_limit_ms": 10000,
        "developer_authored_all_task_generators": True,
        "source_code_independent_of_holdout_generator": False,
        "external_blind_verified": False,
        "trusted_timestamp_verified": False,
        "lottery_predictive_advantage": "NOT_ESTABLISHED",
        "models": models,
        "paired_portfolio_only": a,
        "paired_gate_only": b,
        "exploratory_exact_mcnemar_two_sided_p": _mcnemar(a, b),
        "small_sample_warning": "Only eight developer-authored tasks; exploratory statistics, not external science.",
        "rows": rows,
        "records_without_runtime_sha256": digest([
            {k:v for k,v in r.items() if k != "worker_actual_component_wall_ms_untrusted"}
            for r in rows]),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    result = run(args.out)
    print(json.dumps({k: result[k] for k in ("schema", "models", "tasks",
                    "external_blind_verified", "records_without_runtime_sha256")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
