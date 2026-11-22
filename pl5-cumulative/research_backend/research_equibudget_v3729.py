"""V3.7.29 EQUAL-TOTAL-BUDGET three-role trial adapter, no new solver algorithms.

Issuer: sign *two* fixed challenges with 10000ms and 5000ms budgets.
Solver: freeze independent V25/V26 10000ms standalone runs AND a separate
        5000ms-per-arm portfolio run. PRIVATE data never enters this stage.
Grader: verify BOTH solver freezes before revealing any labels; independently
        settle both then extract the two standalone 10000ms scores and
        the frozen portfolio's 5000+5000ms score.

An actual external blind study also needs independent issuer/grader identities,
private-label custody, locked execution image, and authenticated timestamp.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from research_signed_blind_v3728 import (
    issue, freeze, settle, verify_freeze, verify_settlement,
    _sha, _read, _fingerprint,
)
from research_blind_protocol_v3729 import BUDGETS, ARMS, write_new

STANDALONE = "standalone_10s"
PORTFOLIO = "portfolio_5s_each"
ATT10 = "issuer_10s.json"
ATT5 = "issuer_5s.json"


def issue_pair(public_file, backend_root, issuer_private, issuer_public, out):
    root = Path(out)
    root.mkdir(parents=True, exist_ok=False)
    issue(public_file, backend_root, issuer_private, issuer_public,
          root / ATT10, 10000)
    issue(public_file, backend_root, issuer_private, issuer_public,
          root / ATT5, 5000)
    return {"stage": "ISSUED", "budgets_ms": {"standalone": 10000, "portfolio_each": 5000},
            "attestation_sha256": {ATT10: _sha((root / ATT10).read_bytes()),
                                   ATT5: _sha((root / ATT5).read_bytes())},
            "external_blind_verified": False}


def _preflight(public_file, backend_root, attest_dir, issuer_public,
               solver_public, out):
    root = Path(out)
    attest = Path(attest_dir)
    for name, folder in ((ATT10, STANDALONE), (ATT5, PORTFOLIO)):
        verify_freeze(public_file, backend_root, attest / name, issuer_public,
                      solver_public, root / folder)
    return True


def freeze_pair(public_file, backend_root, attest_dir, issuer_public,
                solver_private, solver_public, out):
    root = Path(out)
    root.mkdir(parents=True, exist_ok=False)
    att = Path(attest_dir)
    freeze(public_file, backend_root, att / ATT10, issuer_public,
           solver_private, solver_public, root / STANDALONE)
    freeze(public_file, backend_root, att / ATT5, issuer_public,
           solver_private, solver_public, root / PORTFOLIO)
    _preflight(public_file, backend_root, att, issuer_public, solver_public, root)
    return {"stage": "FROZEN_BOTH_BEFORE_GRADING", "private_answers_seen": False,
            "evidence_grade": "SIGNED_HANDOFF_IDENTITY_UNVERIFIED",
            "external_blind_verified": False}


def _row(root, source_arm, ledger_arm, budget):
    score = _read(root / "score.json")["arms"][source_arm]
    run = _read(root / "solver_manifest.json")
    protocol = _read(root / "protocol.json")
    expected_per_arm = budget if source_arm != "frozen_portfolio" else budget // 2
    if protocol["budget_ms_per_arm"] != expected_per_arm:
        raise ValueError("wrong underlying worker budget")
    for arm, event in run["arms"].items():
        if type(event.get("allowed_budget_ms")) is not int or \
           event["allowed_budget_ms"] != expected_per_arm:
            raise ValueError("worker budget does not match signed protocol")
    # Model workers have individual measured wall-time receipts, but the
    # runner's local clock is not a trusted third-party hardware attestation.
    if source_arm == "frozen_portfolio":
        measured = [run["arms"]["v3725_ring"]["wall_ms"],
                    run["arms"]["v3726_gate"]["wall_ms"]]
    else:
        measured = [run["arms"][source_arm]["wall_ms"]]
    if any(type(v) not in (int, float) or v < 0 for v in measured):
        raise ValueError("missing or invalid worker timing")
    return {
        "arm": ledger_arm, "status": score["status"],
        "holdout_errors": score["holdout_errors"],
        "holdout_cells": score["holdout_cells"], "budget_ms": budget,
        "receipt_verified": True,  # V3.7.28 signed sequence verified below
        "measured_worker_wall_ms": measured,
        "measurement_trust": "UNVERIFIED_LOCAL_WALL_CLOCK",
    }


def settle_pair(public_file, private_file, backend_root, attest_dir,
                issuer_public, solver_public, grader_private, grader_public,
                out):
    root = Path(out)
    att = Path(attest_dir)
    # Strictly preflight both signed freezes before either private test is opened.
    _preflight(public_file, backend_root, att, issuer_public, solver_public, root)
    for name, folder in ((ATT10, STANDALONE), (ATT5, PORTFOLIO)):
        settle(public_file, private_file, backend_root, att / name, issuer_public,
               solver_public, grader_private, grader_public, root / folder)
    for name, folder in ((ATT10, STANDALONE), (ATT5, PORTFOLIO)):
        verified = verify_settlement(public_file, backend_root, att / name,
                                     issuer_public, solver_public,
                                     grader_public, root / folder)
        if verified["signed_evidence_verified"] is not True:
            raise ValueError("invalid signed freeze or grade receipt")
    rows = [
        _row(root / STANDALONE, "v3725_ring", "v3725_ring", 10000),
        _row(root / STANDALONE, "v3726_gate", "v3726_gate", 10000),
        _row(root / PORTFOLIO, "frozen_portfolio", "frozen_portfolio", 10000),
    ]
    # Keep a separate budget telemetry report, since the V3.7.29 panel score
    # ledger has a deliberately narrow schema. Never silently equate an
    # attested budget declaration with validated independent clock evidence.
    actual = {"schema": "pl5-v3729-equal-budget-telemetry-1",
              "task_id": _read(public_file)["task_id"],
              "arms": {r["arm"]: {"budget_ms": r["budget_ms"],
                                  "observed_component_wall_ms": r["measured_worker_wall_ms"],
                                  "measurement_trust": r["measurement_trust"]}
                       for r in rows},
              "standalone_signed_grader_sha256":
                  _sha((root / STANDALONE / "grader_signed_receipt.json").read_bytes()),
              "portfolio_signed_grader_sha256":
                  _sha((root / PORTFOLIO / "grader_signed_receipt.json").read_bytes()),
              "third_party_identity_verified": False,
              "trusted_timestamp_verified": False,
              "lottery_predictive_advantage": "NOT_ESTABLISHED"}
    write_new(root / "equal_budget_telemetry.json", actual)
    # Return score rows, but the grader/issuer must externally establish
    # task membership, previous manifest SHA and independence before use.
    for row in rows:
        row.pop("measured_worker_wall_ms")
        row.pop("measurement_trust")
        row["task_id"] = actual["task_id"]
    return {"stage": "SIGNED_GRADED", "rows": rows,
            "external_blind_verified": False,
            "grader_public_fingerprint_sha256": _fingerprint(grader_public),
            "telemetry_sha256": _sha((root / "equal_budget_telemetry.json").read_bytes())}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sp = ap.add_subparsers(dest="action", required=True)
    for name in ("issue", "freeze", "grade"):
        p = sp.add_parser(name)
        p.add_argument("--public", required=True, type=Path)
        p.add_argument("--backend", required=True, type=Path)
        p.add_argument("--out", required=True, type=Path)
        if name != "issue":
            p.add_argument("--attestations", required=True, type=Path)
            p.add_argument("--issuer-public", required=True, type=Path)
            p.add_argument("--solver-public", required=True, type=Path)
        if name == "issue":
            p.add_argument("--issuer-private", required=True, type=Path)
            p.add_argument("--issuer-public", required=True, type=Path)
        if name == "freeze":
            p.add_argument("--solver-private", required=True, type=Path)
        if name == "grade":
            p.add_argument("--private", required=True, type=Path)
            p.add_argument("--grader-private", required=True, type=Path)
            p.add_argument("--grader-public", required=True, type=Path)
    args = ap.parse_args()
    if args.action == "issue":
        result = issue_pair(args.public, args.backend, args.issuer_private,
                            args.issuer_public, args.out)
    elif args.action == "freeze":
        result = freeze_pair(args.public, args.backend, args.attestations,
                             args.issuer_public, args.solver_private,
                             args.solver_public, args.out)
    else:
        result = settle_pair(args.public, args.private, args.backend,
                             args.attestations, args.issuer_public,
                             args.solver_public, args.grader_private,
                             args.grader_public, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
