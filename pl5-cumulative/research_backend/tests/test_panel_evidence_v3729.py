"""V3.7.29 independent file-level batch receipts: synthetic developer fixtures ONLY."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmark_hard_budget_v3727 import task, SEEDS
from research_open_grammar_v3725 import prepare
from research_signed_blind_v3728 import keygen
from research_equibudget_v3729 import issue_pair, freeze_pair, settle_pair
from research_blind_protocol_v3729 import (
    SCHEMA, META_SCHEMA, check_public_panel, digest, file_sha,
    preregister, summarize, write_new,
)
from research_panel_evidence_v3729 import assemble, AUDIT_SCHEMA
from research_blind_ledger_v3729 import sign_grade_ledger, verify_grade_ledger

BACKEND = Path(__file__).resolve().parents[1]
COMMIT = "c0e38040ec5f389d6444e64b90e7adc42adfca62"


def setup_panel(tmp_path):
    """Exactly one developer-signed task, 99 *intentionally missing* synthetic cases.

    Remaining public entries are NOT real external challenge solutions.
    """
    key_root = tmp_path / "PRIVATE_KEYS_NOT_EXPORTED"
    key_root.mkdir()
    keys = {}
    for role in ("issuer", "solver", "grader"):
        keys[role] = (key_root / (role + ".key"), tmp_path / (role + ".pub"))
        keygen(*keys[role])

    original = tmp_path / "dev_task.json"
    original.write_text(json.dumps(task("equal_gate", SEEDS[0])), encoding="utf-8")
    prepare(original, tmp_path / "one_public", key_root / "holdout")
    template = json.loads((tmp_path / "one_public" / "public_challenge.json").read_text())
    real_id = template["task_id"]

    public_root = tmp_path / "public"
    public_root.mkdir()
    task_ids = [real_id] + [f"internal_missing_{i:03d}" for i in range(1, 100)]
    manifest = {"schema": SCHEMA + ":public-manifest", "tasks": []}
    for task_id in task_ids:
        entry = dict(template)
        entry["task_id"] = task_id
        if task_id != real_id:
            entry["holdout_commitment"] = digest(
                ["INTERNAL_FAKE_PUBLIC_ONLY_HOLDOUT", task_id])
        entry["protocol_sha256"] = digest({
            k: v for k, v in entry.items() if k != "protocol_sha256"})
        filename = public_root / (task_id + ".json")
        write_new(filename, entry)
        manifest["tasks"].append(
            {"task_id": task_id, "public_sha256": file_sha(filename)})

    pfile = tmp_path / "prereg.json"
    plan = preregister(COMMIT, "a" * 64, pfile)
    assert check_public_panel(plan, manifest, public_root)["tasks_validated"] == 100

    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    study = evidence_root / real_id
    study.mkdir()
    public = public_root / (real_id + ".json")
    private = key_root / "holdout" / "private_challenge.json"
    issue_pair(public, BACKEND, *keys["issuer"], study / "issuer_receipts")
    freeze_pair(public, BACKEND, study / "issuer_receipts",
                keys["issuer"][1], *keys["solver"], study / "solver")
    settle_pair(public, private, BACKEND, study / "issuer_receipts",
                keys["issuer"][1], keys["solver"][1],
                *keys["grader"], study / "solver")
    return plan, manifest, public_root, evidence_root, keys, real_id


def audit(bundle):
    plan, manifest, pub, evidence, keys, _ = bundle
    return assemble(plan, manifest, pub, evidence, BACKEND,
                    keys["issuer"][1], keys["solver"][1], keys["grader"][1])


def test_signed_100_task_ledger_tracks_99_missing_without_fake_results(tmp_path):
    bundle = setup_panel(tmp_path)
    ledger, detail = audit(bundle)
    plan, manifest, _, _, keys, real_id = bundle
    assert detail["schema"] == AUDIT_SCHEMA
    assert detail["task_count_committed"] == 100
    assert detail["task_count_evidence_verified"] == 1
    assert detail["task_count_no_submission"] == 99
    assert len(detail["missing_task_ids"]) == 99
    assert len(ledger["results"]) == 3
    assert detail["ledger_sha256"] == digest(ledger)
    assert detail["external_blind_verified"] is False
    assert detail["individual_v3728_cryptographic_signatures_checked"] is True
    assert {r["task_id"] for r in ledger["results"]} == {real_id}

    signature = tmp_path / "grader_signed_ledger.json"
    sign_grade_ledger(plan, manifest, ledger, *keys["grader"], signature)
    receipt = verify_grade_ledger(plan, manifest, ledger, json.loads(signature.read_text()),
                                  keys["grader"][1])
    assert receipt["grade_ledger_signature_verified"] is True
    assert receipt["individual_worker_receipts_verified"] is False
    category = {x["task_id"]: ("negative_control" if i in range(1, 26) else "structured")
                for i, x in enumerate(manifest["tasks"])}
    summary = summarize(
        plan, {"schema": META_SCHEMA, "categories": category}, ledger, manifest)
    assert summary["methods"]["v3725_ring"]["missing_submissions"] == 99
    assert summary["methods"]["v3726_gate"]["missing_submissions"] == 99
    assert summary["methods"]["frozen_portfolio"]["missing_submissions"] == 99
    assert summary["external_blind_verified"] is False


def test_corrupted_grader_score_is_not_accepted_into_ledger(tmp_path):
    bundle = setup_panel(tmp_path)
    real_id = bundle[-1]
    score = bundle[3] / real_id / "solver" / "standalone_10s" / "score.json"
    score.write_bytes(score.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="grader receipt mismatch"):
        audit(bundle)


def test_unregistered_evidence_file_rejected(tmp_path):
    bundle = setup_panel(tmp_path)
    (bundle[3] / "unregistered.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="unregistered"):
        audit(bundle)
