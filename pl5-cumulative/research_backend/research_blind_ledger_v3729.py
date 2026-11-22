"""V3.7.29 signed aggregate score-ledger handoff, NOT independent certification.

This module verifies Ed25519 authorship and exact byte-equivalent JSON-content
bindings between the preregistration, public manifest and grade ledger. It does
NOT validate individual worker receipts or timestamps, nor authenticate a grader
as independent. The source-complete solver stays frozen at V3.7.28.

Signing must be done on the grader's separately controlled machine after
individual grader/solver evidence has been independently examined.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path

from research_blind_protocol_v3729 import (
    SCHEMA, RESULT_SCHEMA, digest, read, write_new, plan_checked,
    HEX64, N, TASK_ID, ARMS,
)

ENVELOPE = SCHEMA + ":grade-ledger-envelope"
PAYLOAD = SCHEMA + ":grade-ledger-signature"
KEYS = {
    "schema", "preregistration_sha256", "public_manifest_sha256",
    "score_ledger_sha256", "grader_public_fingerprint_sha256",
    "issuer_independence_verified", "trusted_timestamp_verified",
    "underlying_worker_receipts_independently_verified",
}


def _crypto():
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey, Ed25519PublicKey,
        )
    except ImportError as exc:
        raise RuntimeError("Install cryptography>=43 for signed evidence") from exc
    return InvalidSignature, serialization, Ed25519PrivateKey, Ed25519PublicKey


def _pub(public_path):
    _, serialization, _, Pub = _crypto()
    public = serialization.load_pem_public_key(Path(public_path).read_bytes())
    if not isinstance(public, Pub):
        raise ValueError("Ed25519 grader public key required")
    return public


def _fingerprint(pub):
    _, serialization, _, _ = _crypto()
    raw = pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()


def _validate_bindings(plan, manifest, ledger):
    plan_checked(plan)
    if manifest.get("schema") != SCHEMA + ":public-manifest":
        raise ValueError("invalid public manifest schema")
    entries = manifest.get("tasks")
    if not isinstance(entries, list) or len(entries) != N:
        raise ValueError("exactly 100 public task commitments required")
    seen = set()
    for entry in entries:
        if (not isinstance(entry, dict) or
            set(entry) != {"task_id", "public_sha256"}):
            raise ValueError("invalid public manifest row")
        task_id, hash_value = entry["task_id"], entry["public_sha256"]
        if (not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id) or
            not isinstance(hash_value, str) or not HEX64.fullmatch(hash_value) or
            task_id in seen):
            raise ValueError("invalid or duplicated task id/hash")
        seen.add(task_id)
    if ledger.get("schema") != RESULT_SCHEMA:
        raise ValueError("invalid result ledger schema")
    if ledger.get("solver_source_commit") != plan["solver_source_commit"]:
        raise ValueError("wrong source commit in score ledger")
    if ledger.get("preregistration_sha256") != digest(plan):
        raise ValueError("score ledger wrong preregistration")
    if ledger.get("public_manifest_sha256") != digest(manifest):
        raise ValueError("score ledger wrong public task manifest")
    rows = ledger.get("results")
    if not isinstance(rows, list) or len(rows) > len(ARMS) * N:
        raise ValueError("invalid or oversized score list")
    used = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("score row must be object")
        key = (row.get("task_id"), row.get("arm"))
        if (key[0] not in seen or key[1] not in ARMS or key in used):
            raise ValueError("unknown or duplicate task/arm in score")
        used.add(key)


def sign_grade_ledger(plan, manifest, ledger, grader_private, grader_public, out):
    """Bind a grader-controlled key to the study hashes without certifying identity."""
    _, serialization, Priv, _ = _crypto()
    _validate_bindings(plan, manifest, ledger)
    private = serialization.load_pem_private_key(Path(grader_private).read_bytes(), password=None)
    if not isinstance(private, Priv):
        raise ValueError("Ed25519 private key required")
    public = _pub(grader_public)
    if private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw) != \
       public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw):
        raise ValueError("grader private/public key mismatch")
    body = {
        "schema": PAYLOAD,
        "preregistration_sha256": digest(plan),
        "public_manifest_sha256": digest(manifest),
        "score_ledger_sha256": digest(ledger),
        "grader_public_fingerprint_sha256": _fingerprint(public),
        "issuer_independence_verified": False,
        "trusted_timestamp_verified": False,
        "underlying_worker_receipts_independently_verified": False,
    }
    signature = private.sign(json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8"))
    evidence = {
        "schema": ENVELOPE, "payload": body, "signature_alg": "Ed25519",
        "signature_b64": base64.b64encode(signature).decode("ascii"),
    }
    write_new(out, evidence)
    return {"schema": SCHEMA + ":signed-ledger-created",
            "grader_public_fingerprint_sha256": _fingerprint(public),
            "ledger_signature_created": True,
            "independent_grader_identity_verified": False}


def verify_grade_ledger(plan, manifest, ledger, evidence, grader_public):
    """Cryptographic integrity check; cannot prove true custody or grading."""
    InvalidSignature, _, _, _ = _crypto()
    _validate_bindings(plan, manifest, ledger)
    if (not isinstance(evidence, dict) or
        set(evidence) != {"schema", "payload", "signature_alg", "signature_b64"} or
        evidence.get("schema") != ENVELOPE or evidence.get("signature_alg") != "Ed25519"):
        raise ValueError("invalid signed grade envelope")
    body = evidence.get("payload")
    if not isinstance(body, dict) or set(body) != KEYS or body.get("schema") != PAYLOAD:
        raise ValueError("invalid grade signature payload")
    pub = _pub(grader_public)
    expected = {
        "preregistration_sha256": digest(plan),
        "public_manifest_sha256": digest(manifest),
        "score_ledger_sha256": digest(ledger),
        "grader_public_fingerprint_sha256": _fingerprint(pub),
    }
    if any(body.get(k) != v for k, v in expected.items()):
        raise ValueError("signed grade ledger does not match frozen evidence")
    for k in ("issuer_independence_verified", "trusted_timestamp_verified",
              "underlying_worker_receipts_independently_verified"):
        if body.get(k) is not False:
            raise ValueError("unsupported third-party evidence claim")
    signature_b64 = evidence.get("signature_b64")
    if not isinstance(signature_b64, str) or len(signature_b64) > 512:
        raise ValueError("invalid grade signature encoding")
    try:
        raw = base64.b64decode(signature_b64, validate=True)
        if len(raw) != 64:
            raise ValueError("invalid Ed25519 signature length")
        pub.verify(raw, json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False).encode("utf-8"))
    except (InvalidSignature, ValueError, binascii.Error) as exc:
        raise ValueError("grader signature verification failed") from exc
    return {
        "schema": SCHEMA + ":grade-ledger-integrity-check",
        "grade_ledger_signature_verified": True,
        "grader_public_fingerprint_sha256": _fingerprint(pub),
        "preregistration_sha256": digest(plan),
        "public_manifest_sha256": digest(manifest),
        "score_ledger_sha256": digest(ledger),
        "individual_worker_receipts_verified": False,
        "grader_identity_independently_verified": False,
        "trusted_timestamp_verified": False,
        "external_blind_verified": False,
        "lottery_predictive_advantage": "NOT_ESTABLISHED",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="action", required=True)
    for name in ("sign", "verify"):
        c = commands.add_parser(name)
        c.add_argument("--plan", required=True, type=Path)
        c.add_argument("--manifest", required=True, type=Path)
        c.add_argument("--ledger", required=True, type=Path)
        c.add_argument("--grader-public", required=True, type=Path)
        c.add_argument("--out", required=True, type=Path)
        if name == "sign":
            c.add_argument("--grader-private", required=True, type=Path)
        else:
            c.add_argument("--attestation", required=True, type=Path)
    args = p.parse_args()
    plan, manifest, ledger = read(args.plan), read(args.manifest), read(args.ledger)
    if args.action == "sign":
        result = sign_grade_ledger(plan, manifest, ledger,
                                   args.grader_private, args.grader_public, args.out)
    else:
        result = verify_grade_ledger(plan, manifest, ledger,
                                     read(args.attestation), args.grader_public)
        write_new(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
