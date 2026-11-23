"""V3.7.29 cryptographic ledger tests: synthetic metadata, not external trial."""
import base64
import copy
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from research_blind_protocol_v3729 import SCHEMA, RESULT_SCHEMA, digest, preregister, read
from research_blind_ledger_v3729 import sign_grade_ledger, verify_grade_ledger

SOURCE = "c0e38040ec5f389d6444e64b90e7adc42adfca62"


def material(tmp_path):
    plan_file = tmp_path / "plan.json"
    plan = preregister(SOURCE, "a" * 64, plan_file)
    manifest = {"schema": SCHEMA + ":public-manifest",
                "tasks": [{"task_id": f"task_{i:03d}", "public_sha256": "b" * 64}
                          for i in range(100)]}
    ledger = {"schema": RESULT_SCHEMA, "solver_source_commit": SOURCE,
              "preregistration_sha256": digest(plan),
              "public_manifest_sha256": digest(manifest),
              "results": [{"task_id": "task_000", "arm": "v3726_gate",
                           "status": "ABSTAIN", "holdout_errors": None,
                           "holdout_cells": 0, "budget_ms": 10000,
                           "receipt_verified": True}]}
    return plan, manifest, ledger


def keys(tmp_path, prefix):
    private = Ed25519PrivateKey.generate()
    secret_path = tmp_path / f"{prefix}.key"
    public_path = tmp_path / f"{prefix}.pub"
    secret_path.write_bytes(private.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    public_path.write_bytes(private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    return secret_path, public_path


def signed_fixture(tmp_path):
    plan, manifest, ledger = material(tmp_path)
    priv, pub = keys(tmp_path, "grader")
    out = tmp_path / "grade.attestation.json"
    created = sign_grade_ledger(plan, manifest, ledger, priv, pub, out)
    assert created["independent_grader_identity_verified"] is False
    return plan, manifest, ledger, read(out), priv, pub, out


def test_signature_binds_grade_to_preregistration_and_manifest(tmp_path):
    plan, manifest, ledger, att, _, pub, _ = signed_fixture(tmp_path)
    receipt = verify_grade_ledger(plan, manifest, ledger, att, pub)
    assert receipt["grade_ledger_signature_verified"] is True
    assert receipt["external_blind_verified"] is False
    assert receipt["individual_worker_receipts_verified"] is False


def test_ledger_tampering_detected(tmp_path):
    plan, manifest, ledger, att, _, pub, _ = signed_fixture(tmp_path)
    ledger["results"][0]["status"] = "EVALUATED"
    with pytest.raises(ValueError, match="signed grade ledger does not match"):
        verify_grade_ledger(plan, manifest, ledger, att, pub)


def test_wrong_grader_public_key_rejected(tmp_path):
    plan, manifest, ledger, att, _, _, _ = signed_fixture(tmp_path)
    _, wrong_pub = keys(tmp_path, "wrong")
    with pytest.raises(ValueError, match="signed grade ledger does not match"):
        verify_grade_ledger(plan, manifest, ledger, att, wrong_pub)


def test_signature_bit_tampering_detected(tmp_path):
    plan, manifest, ledger, att, _, pub, _ = signed_fixture(tmp_path)
    raw = bytearray(base64.b64decode(att["signature_b64"]))
    raw[0] ^= 1
    att["signature_b64"] = base64.b64encode(raw).decode("ascii")
    with pytest.raises(ValueError, match="signature verification failed"):
        verify_grade_ledger(plan, manifest, ledger, att, pub)


def test_claiming_external_validation_rejected_even_if_payload_has_claim(tmp_path):
    plan, manifest, ledger, att, _, pub, _ = signed_fixture(tmp_path)
    att["payload"]["trusted_timestamp_verified"] = True
    with pytest.raises(ValueError, match="unsupported third-party"):
        verify_grade_ledger(plan, manifest, ledger, att, pub)


def test_modified_plan_rejected(tmp_path):
    plan, manifest, ledger, att, _, pub, _ = signed_fixture(tmp_path)
    different = copy.deepcopy(plan)
    different["environment_lock_sha256"] = "c" * 64
    with pytest.raises(ValueError, match="wrong preregistration"):
        verify_grade_ledger(different, manifest, ledger, att, pub)


def test_different_manifest_and_ledger_rejected(tmp_path):
    plan, manifest, ledger, att, _, pub, _ = signed_fixture(tmp_path)
    manifest["tasks"][0]["public_sha256"] = "d" * 64
    with pytest.raises(ValueError, match="wrong public task"):
        verify_grade_ledger(plan, manifest, ledger, att, pub)


def test_repeated_attestation_cannot_overwrite(tmp_path):
    plan, manifest, ledger, att, priv, pub, path = signed_fixture(tmp_path)
    with pytest.raises(FileExistsError):
        sign_grade_ledger(plan, manifest, ledger, priv, pub, path)


def test_grader_private_public_mismatch_rejected(tmp_path):
    plan, manifest, ledger = material(tmp_path)
    priv, _ = keys(tmp_path, "grader")
    _, other_pub = keys(tmp_path, "other")
    with pytest.raises(ValueError, match="key mismatch"):
        sign_grade_ledger(plan, manifest, ledger, priv, other_pub,
                          tmp_path / "not_created.json")


def test_duplicate_task_in_ledger_rejected(tmp_path):
    plan, manifest, ledger = material(tmp_path)
    ledger["results"].append(copy.deepcopy(ledger["results"][0]))
    priv, pub = keys(tmp_path, "grader")
    with pytest.raises(ValueError, match="duplicate"):
        sign_grade_ledger(plan, manifest, ledger, priv, pub,
                          tmp_path / "not_created.json")
