"""V3.7.29 pre-registered, fail-closed external panel intake and paired scoring.

This module ONLY checks inputs and aggregates already-settled trial results.
It does not create independent tasks, verify third-party identity, sign receipts,
run solver workers, provide trusted timestamps, or establish lottery advantage.
No raw holdout answers are accepted by the public-panel intake.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

SCHEMA = "pl5-v3729-blind-panel-1"
PUBLIC_VERSION = "pl5-v3725-ring-grammar-1"
RESULT_SCHEMA = "pl5-v3729-score-ledger-1"
META_SCHEMA = "pl5-v3729-private-strata-1"
ARMS = ("v3725_ring", "v3726_gate", "frozen_portfolio")
N = 100
MIN_NEGATIVE = 25
HOLDOUT_CELLS = 36
BUDGETS = {"v3725_ring": 10000, "v3726_gate": 10000,
           "frozen_portfolio": 10000}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TASK_ID = re.compile(r"^[a-zA-Z0-9_.-]{1,128}$")
STATUSES = {"EVALUATED", "ABSTAIN", "TIMED_OUT", "FAILED"}
CATEGORIES = {"structured", "negative_control", "out_of_grammar"}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    p = Path(path)
    if p.stat().st_size > 4_000_000:
        raise ValueError("oversized evidence")
    value = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def write_new(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("x", encoding="utf-8") as f:
        json.dump(value, f, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")


def preregister(source_commit, environment_sha256, out):
    """Freeze the intended solver SOURCE commit before any independent task arrives.

    This self-authored JSON is a *proposal*, not a signed or timestamped attestation.
    """
    if not HEX40.fullmatch(source_commit) or not HEX64.fullmatch(environment_sha256):
        raise ValueError("full source commit and environment SHA256 are mandatory")
    plan = {
        "schema": SCHEMA,
        "solver_source_commit": source_commit,
        "environment_lock_sha256": environment_sha256,
        "min_tasks": N,
        "min_negative_controls": MIN_NEGATIVE,
        "expected_partition": {"train": 48, "validation": 16, "holdout": HOLDOUT_CELLS},
        "arms": list(ARMS),
        "max_total_wall_ms_per_arm_per_task": BUDGETS,
        "portfolio_budget_rule": "two model subprocesses, each <= 5000ms; max 10000ms combined",
        "single_arm_budget_rule": "each standalone model must be separately run at <= 10000ms",
        "primary_endpoint": "exact holdout completion over all preregistered tasks",
        "non_successes": ["ABSTAIN", "FAILED", "TIMED_OUT", "any_holdout_error",
                          "missing_submission"],
        "pairwise_test": "two-sided exact McNemar, preselected comparison "
                         "frozen_portfolio vs v3726_gate",
        "confidence_interval": "Wilson 95 percent, descriptive, not cluster robust",
        "strata": sorted(CATEGORIES),
        "issuer_independence_verified": False,
        "trusted_external_timestamp_verified": False,
        "third_party_blind_study_completed": False,
        "lottery_predictive_advantage": "NOT_ESTABLISHED",
        "disclaimer": "Protocol only; third-party signatures, time provenance, "
                      "private label custody and independently audited hardware "
                      "must be established outside this repository",
    }
    write_new(out, plan)
    return plan


def plan_checked(plan):
    """Reject *all* changes to the protocol's prespecified scientific choices."""
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise ValueError("wrong or modified experiment protocol")
    expected = {
        "min_tasks": N,
        "min_negative_controls": MIN_NEGATIVE,
        "expected_partition": {"train": 48, "validation": 16, "holdout": HOLDOUT_CELLS},
        "arms": list(ARMS),
        "max_total_wall_ms_per_arm_per_task": BUDGETS,
        "portfolio_budget_rule": "two model subprocesses, each <= 5000ms; max 10000ms combined",
        "single_arm_budget_rule": "each standalone model must be separately run at <= 10000ms",
        "primary_endpoint": "exact holdout completion over all preregistered tasks",
        "non_successes": ["ABSTAIN", "FAILED", "TIMED_OUT", "any_holdout_error",
                          "missing_submission"],
        "pairwise_test": "two-sided exact McNemar, preselected comparison "
                         "frozen_portfolio vs v3726_gate",
        "confidence_interval": "Wilson 95 percent, descriptive, not cluster robust",
        "strata": sorted(CATEGORIES),
        "issuer_independence_verified": False,
        "trusted_external_timestamp_verified": False,
        "third_party_blind_study_completed": False,
        "lottery_predictive_advantage": "NOT_ESTABLISHED",
        "disclaimer": "Protocol only; third-party signatures, time provenance, "
                      "private label custody and independently audited hardware "
                      "must be established outside this repository",
    }
    allowed_keys = set(expected) | {
        "schema", "solver_source_commit", "environment_lock_sha256"}
    if set(plan) != allowed_keys or any(
        type(plan.get(k)) is not type(v) or plan[k] != v
        for k, v in expected.items()
    ):
        raise ValueError("protocol constraints changed")
    if not HEX40.fullmatch(str(plan.get("solver_source_commit", ""))):
        raise ValueError("invalid frozen source commit")
    if not HEX64.fullmatch(str(plan.get("environment_lock_sha256", ""))):
        raise ValueError("missing dependency/environment lock hash")
    return plan


def _observations(rows, expected):
    if not isinstance(rows, list) or len(rows) != expected:
        raise ValueError("wrong public partition size")
    seen = set()
    for row in rows:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError("invalid public cell")
        a, b, y = row
        if any(type(x) is not int or not 0 <= x <= 9 for x in (a, b, y)):
            raise ValueError("cell outside digit domain")
        if (a, b) in seen:
            raise ValueError("duplicate coordinate")
        seen.add((a, b))
    return seen


def check_public_panel(plan, manifest, folder):
    """Validate exactly the published train/validation panel; never open private labels.

    The issuer should withhold category/negative-control labels until after freeze.
    """
    plan_checked(plan)
    if manifest.get("schema") != SCHEMA + ":public-manifest":
        raise ValueError("wrong public manifest schema")
    rows = manifest.get("tasks")
    if not isinstance(rows, list) or len(rows) != N:
        raise ValueError("panel must contain exactly 100 task commitments")
    expected = {}
    root = Path(folder).resolve()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"task_id", "public_sha256"}:
            raise ValueError("public manifest must not disclose task strata or labels")
        task_id, sha = row["task_id"], row["public_sha256"]
        if (not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id) or
            not isinstance(sha, str) or not HEX64.fullmatch(sha) or task_id in expected):
            raise ValueError("invalid/duplicate task commitment")
        expected[task_id] = sha
        path = root / (task_id + ".json")
        if path.resolve().parent != root or not path.is_file() or file_sha(path) != sha:
            raise ValueError("missing/modified public challenge")
        task = read(path)
        keys = {"schema", "task_id", "train", "validation",
                "holdout_commitment", "source_description_self_reported",
                "issuer_identity_externally_verified", "evaluation_grade",
                "version", "protocol_sha256"}
        if (set(task) != keys or task["task_id"] != task_id or
            task["schema"] != PUBLIC_VERSION + ":challenge" or
            task["version"] != PUBLIC_VERSION):
            raise ValueError("invalid public challenge; private label leakage")
        if digest({k: v for k, v in task.items() if k != "protocol_sha256"}) != task["protocol_sha256"]:
            raise ValueError("public challenge integrity check failed")
        if not isinstance(task["holdout_commitment"], str) or not HEX64.fullmatch(task["holdout_commitment"]):
            raise ValueError("missing holdout commitment")
        if _observations(task["train"], 48) & _observations(task["validation"], 16):
            raise ValueError("train/validation overlap")
    return {"schema": SCHEMA + ":panel-intake", "tasks_validated": N,
            "public_manifest_sha256": digest(manifest),
            "private_labels_read": False, "external_blind_verified": False}


def _wilson(success, total):
    z = 1.959963984540054
    if total < 1:
        return [0.0, 1.0]
    p = success / total
    den = 1 + z * z / total
    ctr = (p + z * z / (2 * total)) / den
    rad = z * math.sqrt(p * (1-p) / total + z*z / (4*total*total)) / den
    return [max(0.0, ctr-rad), min(1.0, ctr+rad)]


def _mcnemar(a, b):
    discordant = a + b
    if not discordant:
        return 1.0
    tail = sum(math.comb(discordant, k) for k in range(min(a, b)+1))
    return min(1.0, 2 * tail / (2**discordant))


def summarize(plan, private_meta, ledger, public_manifest):
    """Compute descriptive paired results; neither input proves independence.

    An external auditor must first check receipt signatures and evidence custody.
    The panel/task identity must be anchored by the original public manifest.
    """
    plan_checked(plan)
    if (private_meta.get("schema") != META_SCHEMA or
        ledger.get("schema") != RESULT_SCHEMA):
        raise ValueError("invalid score/metadata schema")
    if ledger.get("solver_source_commit") != plan["solver_source_commit"]:
        raise ValueError("score ledger does not match preregistered solver")
    if ledger.get("preregistration_sha256") != digest(plan):
        raise ValueError("ledger preregistration commitment mismatch")
    if (public_manifest.get("schema") != SCHEMA + ":public-manifest" or
        not isinstance(public_manifest.get("tasks"), list) or
        len(public_manifest["tasks"]) != N):
        raise ValueError("invalid task manifest")
    if ledger.get("public_manifest_sha256") != digest(public_manifest):
        raise ValueError("ledger public task commitment mismatch")
    manifest_ids = [r.get("task_id") for r in public_manifest["tasks"]
                    if isinstance(r, dict) and set(r) == {"task_id", "public_sha256"}
                    and isinstance(r.get("task_id"), str)
                    and TASK_ID.fullmatch(r["task_id"])
                    and isinstance(r.get("public_sha256"), str)
                    and HEX64.fullmatch(r["public_sha256"])]
    if len(manifest_ids) != N or len(set(manifest_ids)) != N:
        raise ValueError("invalid or duplicate public task commitments")
    category = private_meta.get("categories")
    if (not isinstance(category, dict) or len(category) != N or
        set(category) != set(manifest_ids)):
        raise ValueError("private strata must exactly match 100 public task IDs")
    if any(not isinstance(k, str) or not TASK_ID.fullmatch(k) or v not in CATEGORIES
           for k, v in category.items()):
        raise ValueError("invalid stratification")
    negative = sum(v == "negative_control" for v in category.values())
    if negative < MIN_NEGATIVE:
        raise ValueError("insufficient negative controls")
    rows = ledger.get("results")
    if not isinstance(rows, list):
        raise ValueError("results array required")
    indexed = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "task_id", "arm", "status", "holdout_errors", "holdout_cells",
            "budget_ms", "receipt_verified"}:
            raise ValueError("malformed result row")
        task_id, arm, status = row["task_id"], row["arm"], row["status"]
        key = (task_id, arm)
        if task_id not in category or arm not in ARMS or key in indexed:
            raise ValueError("unexpected or duplicate score")
        if status not in STATUSES or row["receipt_verified"] is not True:
            raise ValueError("unverified evidence or status")
        if row["budget_ms"] != BUDGETS[arm]:
            raise ValueError("unequal total budget")
        cells, errors = row["holdout_cells"], row["holdout_errors"]
        if status == "EVALUATED":
            if (type(cells) is not int or cells != HOLDOUT_CELLS or
                type(errors) is not int or not 0 <= errors <= cells):
                raise ValueError("invalid evaluated holdout")
        elif cells != 0 or errors is not None:
            raise ValueError("failed/abstained outcome cannot include scored labels")
        indexed[key] = row
    methods = {}
    flags = {}
    for arm in ARMS:
        exact = 0
        accepted = 0
        missing = 0
        null_accept = 0
        flags[arm] = {}
        for task_id, stratum in category.items():
            row = indexed.get((task_id, arm))
            if row is None:
                missing += 1
            success = bool(row and row["status"] == "EVALUATED" and
                           row["holdout_errors"] == 0)
            accepted += int(bool(row and row["status"] == "EVALUATED"))
            exact += int(success)
            null_accept += int(bool(row and row["status"] == "EVALUATED" and
                                    stratum == "negative_control"))
            flags[arm][task_id] = success
        methods[arm] = {
            "denominator": N, "exact_success": exact,
            "accepted": accepted, "missing_submissions": missing,
            "negative_control_accepted": null_accept,
            "negative_control_denominator": negative,
            "wilson95_descriptive": _wilson(exact, N),
        }
    a = b = 0
    for task_id in category:
        portfolio = flags["frozen_portfolio"][task_id]
        gate = flags["v3726_gate"][task_id]
        a += int(portfolio and not gate)
        b += int(gate and not portfolio)
    return {
        "schema": SCHEMA + ":unverified-aggregated-report",
        "preregistration_sha256": digest(plan),
        "metadata_sha256": digest(private_meta),
        "public_manifest_sha256": digest(public_manifest),
        "score_ledger_sha256": digest(ledger),
        "tasks": N,
        "negative_controls": negative,
        "methods": methods,
        "primary_pair": "frozen_portfolio vs v3726_gate at same 10000ms total",
        "discordant_portfolio_only": a,
        "discordant_gate_only": b,
        "exact_mcnemar_two_sided_p": _mcnemar(a, b),
        "cluster_robust_inference": "NOT_PERFORMED",
        "external_blind_verified": False,
        "third_party_identity_verified": False,
        "trusted_timestamp_verified": False,
        "lottery_predictive_advantage": "NOT_ESTABLISHED",
        "warning": "Aggregating self-reported records never authenticates blind custody, "
                   "signatures, timestamps, hardware budgets, or 3rd-party independence.",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="action", required=True)
    p = sub.add_parser("preregister")
    p.add_argument("--source-commit", required=True)
    p.add_argument("--environment-sha256", required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("check-public")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("summarize")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--private-metadata", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--signed-ledger", type=Path, required=True)
    p.add_argument("--grader-public", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.action == "preregister":
        result = preregister(args.source_commit, args.environment_sha256, args.out)
    elif args.action == "check-public":
        result = check_public_panel(read(args.plan), read(args.manifest), args.folder)
        write_new(args.out, result)
    else:
        # A self-reported receipt_verified=true flag is not sufficient:
        # require Ed25519 ledger integrity before CLI reporting.
        from research_blind_ledger_v3729 import verify_grade_ledger
        plan = read(args.plan)
        ledger = read(args.ledger)
        manifest = read(args.manifest)
        verified = verify_grade_ledger(
            plan, manifest, ledger, read(args.signed_ledger), args.grader_public)
        result = summarize(plan, read(args.private_metadata), ledger, manifest)
        result["grade_ledger_signature_verified"] = verified["grade_ledger_signature_verified"]
        result["grader_public_fingerprint_sha256"] = verified["grader_public_fingerprint_sha256"]
        result["individual_worker_receipts_verified"] = False
        write_new(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
