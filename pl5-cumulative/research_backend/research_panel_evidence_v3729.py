"""V3.7.29 batch evidence auditor: verify each signed task before ledger assembly.

This is a file-level cryptographic consistency check, NOT a certification of
external independence, timestamps, original source authenticity or runtime.
The grader must independently retain original holdout labels and custody proof.
Absent submissions count as missing, never silently disappear from the panel.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_blind_protocol_v3729 import (
    SCHEMA, RESULT_SCHEMA, ARMS, check_public_panel, digest, read, write_new,
)
from research_signed_blind_v3728 import verify_settlement, _fingerprint, _sha
from research_equibudget_v3729 import STANDALONE, PORTFOLIO, ATT10, ATT5, _row

AUDIT_SCHEMA = SCHEMA + ":verified-receipt-coverage-1"
REQUIRED = ("issuer_receipts", "solver")


def _safe_child(root: Path, name: str) -> Path:
    path = root / name
    if path.resolve().parent != root.resolve():
        raise ValueError("evidence path escapes declared root")
    return path


def _hash_file(path: Path) -> str:
    if not path.is_file():
        raise ValueError("missing signed evidence file: " + path.name)
    return _sha(path.read_bytes())


def _verify_one(task_id, public, study_dir, backend, issuer_pub, solver_pub, grader_pub):
    """Read both signed settlement trees and rebuild scores from VERIFIED files."""
    att = study_dir / REQUIRED[0]
    root = study_dir / REQUIRED[1]
    signed_hashes = {}
    for filename, subdir in ((ATT10, STANDALONE), (ATT5, PORTFOLIO)):
        issuer_att = att / filename
        solver = root / subdir
        verified = verify_settlement(
            public, backend, issuer_att, issuer_pub, solver_pub, grader_pub, solver)
        if verified.get("signed_evidence_verified") is not True:
            raise ValueError("individual V3.7.28 signatures are not verified")
        signed_hashes[subdir] = {
            "issuer_attestation_sha256": _hash_file(issuer_att),
            "solver_signed_receipt_sha256":
                _hash_file(solver / "solver_signed_receipt.json"),
            "grader_signed_receipt_sha256":
                _hash_file(solver / "grader_signed_receipt.json"),
            "score_json_sha256": _hash_file(solver / "score.json"),
        }
    rows = [
        _row(root / STANDALONE, "v3725_ring", "v3725_ring", 10000),
        _row(root / STANDALONE, "v3726_gate", "v3726_gate", 10000),
        _row(root / PORTFOLIO, "frozen_portfolio", "frozen_portfolio", 10000),
    ]
    if [r["arm"] for r in rows] != list(ARMS):
        raise ValueError("incomplete/misaligned algorithm comparison")
    for row in rows:
        if row.pop("measurement_trust") != "UNVERIFIED_LOCAL_WALL_CLOCK":
            raise ValueError("unexpected timing provenance")
        row.pop("measured_worker_wall_ms")
        row["task_id"] = task_id
    return rows, signed_hashes


def assemble(plan, manifest, public_dir, evidence_dir, backend_root,
             issuer_pub, solver_pub, grader_pub):
    """Build one complete-coverage *internal/unverified* ledger.

    Missing entire task directories are recorded as missing, not omitted from
    the audit report; partial/tampered task directories fail the whole run.
    """
    check_public_panel(plan, manifest, public_dir)
    backend = Path(backend_root).resolve()
    public_root = Path(public_dir).resolve()
    evidence_root = Path(evidence_dir).resolve()
    if not evidence_root.is_dir():
        raise FileNotFoundError("evidence root absent")
    fp = {
        "issuer": _fingerprint(issuer_pub),
        "solver": _fingerprint(solver_pub),
        "grader": _fingerprint(grader_pub),
    }
    if len(set(fp.values())) != 3:
        raise ValueError("issuer/solver/grader public keys must be distinct")
    ids = [entry["task_id"] for entry in manifest["tasks"]]
    if any(node.name not in ids for node in evidence_root.iterdir()):
        raise ValueError("unregistered task evidence directory or file")
    rows = []
    examined = {}
    missing = []
    for task_id in ids:
        public = _safe_child(public_root, task_id + ".json")
        root = _safe_child(evidence_root, task_id)
        if not root.exists():
            missing.append(task_id)
            continue
        if not root.is_dir():
            raise ValueError("task evidence must be directory")
        actual, file_hashes = _verify_one(
            task_id, public, root, backend, issuer_pub, solver_pub, grader_pub)
        rows.extend(actual)
        examined[task_id] = file_hashes
    ledger = {
        "schema": RESULT_SCHEMA,
        "solver_source_commit": plan["solver_source_commit"],
        "preregistration_sha256": digest(plan),
        "public_manifest_sha256": digest(manifest),
        "results": rows,
    }
    audit = {
        "schema": AUDIT_SCHEMA,
        "task_count_committed": len(ids),
        "task_count_evidence_verified": len(examined),
        "task_count_no_submission": len(missing),
        "missing_task_ids": missing,
        "verified_per_task_receipts": examined,
        "key_fingerprints_sha256": fp,
        "ledger_sha256": digest(ledger),
        "public_manifest_sha256": digest(manifest),
        "all_task_ids_accounted_for": len(missing) + len(examined) == len(ids),
        "individual_v3728_cryptographic_signatures_checked": bool(examined),
        "independent_issuer_identity_verified": False,
        "private_label_custody_independently_verified": False,
        "trusted_timestamp_verified": False,
        "hardware_wall_clock_independently_verified": False,
        "external_blind_verified": False,
        "lottery_predictive_advantage": "NOT_ESTABLISHED",
    }
    return ledger, audit


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--public-dir", required=True, type=Path)
    ap.add_argument("--evidence-dir", required=True, type=Path)
    ap.add_argument("--backend", required=True, type=Path)
    ap.add_argument("--issuer-public", required=True, type=Path)
    ap.add_argument("--solver-public", required=True, type=Path)
    ap.add_argument("--grader-public", required=True, type=Path)
    ap.add_argument("--out-ledger", required=True, type=Path)
    ap.add_argument("--out-audit", required=True, type=Path)
    args = ap.parse_args()
    if args.out_ledger.resolve() == args.out_audit.resolve():
        raise ValueError("audit report and score ledger must use separate files")
    if args.out_ledger.exists() or args.out_audit.exists():
        raise FileExistsError("never overwrite a batch audit output")
    ledger, audit = assemble(
        read(args.plan), read(args.manifest), args.public_dir, args.evidence_dir,
        args.backend, args.issuer_public, args.solver_public, args.grader_public)
    write_new(args.out_ledger, ledger)
    write_new(args.out_audit, audit)
    print(json.dumps({
        "verified_tasks": audit["task_count_evidence_verified"],
        "missing_tasks_counted_as_failure": audit["task_count_no_submission"],
        "external_blind_verified": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
