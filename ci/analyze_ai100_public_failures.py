#!/usr/bin/env python3
"""Read-only public AI100 failure attribution; no private answers or generator code.

Requires the previously user-approved review CSV and public evidence ZIP supplied
separately on the researcher's local machine. Never publish either with this tool.
The output contains category-level counts ONLY; not per-task rules or identities.
The 100 seen tasks are a DEVELOPMENT corpus, NOT an independent new holdout.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

GROUPS = {"A": 20, "B": 25, "C": 20, "D": 10, "E": 25}
ARMS = ("v3725_ring", "v3726_gate")
MODES = ("standalone_10s", "portfolio_5s_each")
SOURCE_COMMIT = "c0e38040ec5f389d6444e64b90e7adc42adfca62"
SOURCE_PREFIX = "signed_frozen_graded_evidence/"


def digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def byte_sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_json(z: ZipFile, path: str, *, internal_hash: bool = False):
    if path not in z.namelist():
        raise ValueError(f"missing public audit file: {path}")
    raw = z.read(path)
    if len(raw) > 4_000_000:
        raise ValueError("oversized public evidence")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("public evidence must be a JSON object")
    if internal_hash:
        expected = result.get("integrity_sha256")
        body = {k: v for k, v in result.items() if k != "integrity_sha256"}
        if not isinstance(expected, str) or expected != digest(body):
            raise ValueError(f"public internal integrity mismatch: {path}")
    return result


def summarize(evidence_zip: Path, review_csv: Path):
    """Attribute observed failures before validation; do not infer grammar limits.

    The category labels are developer-authored and have already been exposed
    during internal study; they MUST NOT be treated as independent test labels.
    """
    with review_csv.open(encoding="utf-8-sig", newline="") as fp:
        entries = list(csv.DictReader(fp))
    if len(entries) != 100:
        raise ValueError("expected exactly 100 developer review rows")
    categories = {}
    for entry in entries:
        task_id = entry["任务ID"]
        group = entry["题组"].split(".")[0]
        if group not in GROUPS or not task_id.startswith("PL5T") or task_id in categories:
            raise ValueError("invalid or duplicated review category/task ID")
        categories[task_id] = group
    if Counter(categories.values()) != GROUPS:
        raise ValueError("approved panel category counts changed")

    counts = {(group, mode, arm): Counter() for group in GROUPS
              for mode in MODES for arm in ARMS}
    with ZipFile(evidence_zip) as z:
        summary = checked_json(z, "public_results/summary.json")
        freeze = checked_json(z, "public_results/all_tasks_freeze_status_manifest.json")
        if (summary.get("source_commit") != SOURCE_COMMIT or
                freeze.get("source_git_commit") != SOURCE_COMMIT or
                summary.get("question_count") != 100 or
                summary.get("evaluation_type") !=
                "AI_AUTHORED_INTERNAL_HOLDOUT_NOT_THIRD_PARTY_BLIND" or
                summary.get("independent_issuer_verified") is not False):
            raise ValueError("wrong AI100 source or evidence grade")
        approved_ids = freeze.get("task_ids")
        receipts = freeze.get("freeze_receipt_sha256")
        if (not isinstance(approved_ids, list) or len(approved_ids) != 100 or
                len(set(approved_ids)) != 100 or set(approved_ids) != set(categories) or
                not isinstance(receipts, dict) or set(receipts) != set(approved_ids)):
            raise ValueError("frozen task manifest does not match approved review")
        if freeze.get("task_freeze_statuses") != {
                "FROZEN": 99, "INTERRUPTED_BEFORE_FREEZE": 1}:
            raise ValueError("unexpected global freeze status")
        # A receipt exists even for the interrupted task. The receipt HASH is
        # never evidence that both solver freeze stages actually completed.
        task_states = {}
        for task_id in approved_ids:
            path = SOURCE_PREFIX + task_id + "/freeze_status.json"
            if path not in z.namelist():
                raise ValueError("missing individual freeze status")
            actual_sha = hashlib.sha256(z.read(path)).hexdigest()
            if actual_sha != receipts[task_id]:
                raise ValueError("individual freeze-status SHA256 mismatch")
            state = checked_json(z, path)
            if state.get("task_id") != task_id or state.get("status") not in (
                    "FROZEN", "INTERRUPTED_BEFORE_FREEZE"):
                raise ValueError("unrecognized per-task frozen state")
            task_states[task_id] = state["status"]
        if Counter(task_states.values()) != Counter(freeze["task_freeze_statuses"]):
            raise ValueError("frozen aggregate status inconsistent with individual receipts")
        for task_id, group in categories.items():
            for mode in MODES:
                for arm in ARMS:
                    c = counts[(group, mode, arm)]
                    c["denominator"] += 1
                    # Never use partial worker files for the interrupted task.
                    if task_states[task_id] != "FROZEN":
                        c["interrupted_before_global_freeze"] += 1
                        continue
                    prefix = SOURCE_PREFIX + task_id + "/solver/" + mode + "/" + arm + "/"
                    fit = checked_json(z, prefix + "fit.json", internal_hash=True)
                    frozen = checked_json(z, prefix + "freeze.json", internal_hash=True)
                    fit_body = {k: v for k, v in fit.items() if k != "integrity_sha256"}
                    if frozen.get("fit_sha256") != digest(fit_body):
                        raise ValueError("freeze-to-fit public hash linkage broken")
                    exact = fit.get("exact_fit_tables")
                    if not isinstance(exact, list):
                        raise ValueError("unreadable candidate list")
                    if not isinstance(fit.get("candidate_evaluations"), int):
                        raise ValueError("missing candidate search workload")
                    if frozen.get("status") not in ("FROZEN", "ABSTAIN"):
                        raise ValueError("unrecognized frozen outcome")
                    c["public_fit_evidence_checked"] += 1
                    c["candidate_evaluations_total"] += fit["candidate_evaluations"]
                    if not exact:
                        c["zero_exact_training_candidates"] += 1
                    else:
                        c["one_or_more_exact_training_candidates"] += 1
                    if frozen["status"] == "FROZEN":
                        c["frozen_model"] += 1
                    elif not exact and frozen.get("reason") == "no_candidate":
                        c["abstained_before_validation_no_candidate"] += 1
                    else:
                        c["abstained_after_candidate_or_other"] += 1

    aggregates = {g: {m: {a: dict(counts[(g, m, a)])
                         for a in ARMS} for m in MODES} for g in GROUPS}
    d = aggregates["D"]
    for mode in MODES:
        for arm in ARMS:
            c = d[mode][arm]
            if (c.get("zero_exact_training_candidates") != 10 or
                    c.get("abstained_before_validation_no_candidate") != 10 or
                    c.get("interrupted_before_global_freeze", 0) != 0):
                raise AssertionError("novel-operator D pattern differs from reported 0/10")
    return {
        "schema": "pl5-ai100-public-failure-attribution-v1",
        "source_commit": SOURCE_COMMIT,
        "evidence_zip_sha256": byte_sha(evidence_zip),
        "review_csv_sha256": byte_sha(review_csv),
        "development_tasks_not_independent": 100,
        "public_evidence_only": True,
        "private_labels_read": False,
        "source_code_modified": False,
        "observed_failure": "D: 10/10 no exact TRAINING candidates for both arms at both budgets",
        "cannot_conclude": "Cannot distinguish grammar nonexpressibility from search/identifiability without new controlled oracle/ablation evidence.",
        "aggregate": aggregates,
        "lottery_predictive_advantage": "NOT_ESTABLISHED",
        "external_blind_verified": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--public-evidence-zip", type=Path, required=True)
    p.add_argument("--review-csv", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError("refuse to overwrite previous audit report")
    result = summarize(args.public_evidence_zip, args.review_csv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    print("AI100 PUBLIC-ONLY ATTRIBUTION PASS; D=10/10 pre-validation no-candidate; no private labels read")


if __name__ == "__main__":
    main()
