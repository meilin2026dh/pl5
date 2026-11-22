"""V3.7.29 protocol safeguards; these are INTERNAL synthetic smoke tests only."""
import json
import copy
from pathlib import Path

import pytest

from research_blind_protocol_v3729 import (
    N, ARMS, BUDGETS, SCHEMA, META_SCHEMA, RESULT_SCHEMA,
    check_public_panel, digest, file_sha, preregister, plan_checked, read, summarize, write_new,
)

COMMIT = "c0e38040ec5f389d6444e64b90e7adc42adfca62"
PUBLIC_MANIFEST = {"schema": SCHEMA + ":public-manifest",
                   "tasks": [{"task_id": f"internal_{i:03d}",
                              "public_sha256": "b" * 64} for i in range(N)]}


def plan(tmp_path):
    path = tmp_path / "prereg.json"
    if not path.exists():
        preregister(COMMIT, "a" * 64, path)
    return read(path)


def panel(tmp_path):
    """100 developer-created public files, without any hidden answers."""
    root = tmp_path / "public"
    root.mkdir()
    manifest = {"schema": SCHEMA + ":public-manifest", "tasks": []}
    for i in range(N):
        task_id = f"internal_{i:03d}"
        rows = [[k // 10, k % 10, (k + i) % 10] for k in range(64)]
        doc = {
            "schema": "pl5-v3725-ring-grammar-1:challenge",
            "task_id": task_id,
            "train": rows[:48], "validation": rows[48:],
            "holdout_commitment": "b" * 64,
            "source_description_self_reported": "INTERNAL_SYNTHETIC_UNIT_TEST",
            "issuer_identity_externally_verified": False,
            "evaluation_grade": "UNVERIFIED_ISSUER_UNTIL_EXTERNAL_AUDIT",
            "version": "pl5-v3725-ring-grammar-1",
        }
        doc["protocol_sha256"] = digest(doc)
        path = root / (task_id + ".json")
        write_new(path, doc)
        manifest["tasks"].append({"task_id": task_id, "public_sha256": file_sha(path)})
    return root, manifest


def scores():
    categories = {f"internal_{i:03d}":
                  "negative_control" if i < 25 else "structured"
                  for i in range(N)}
    metadata = {"schema": META_SCHEMA, "categories": categories}
    rows = []
    for i in range(N):
        for arm in ARMS:
            # Portfolio succeeds on 20; gate succeeds on 10; ring abstains.
            win = (i >= 25 and ((arm == "frozen_portfolio" and i < 45) or
                                (arm == "v3726_gate" and i < 35)))
            rows.append({
                "task_id": f"internal_{i:03d}", "arm": arm,
                "status": "EVALUATED" if win else "ABSTAIN",
                "holdout_errors": 0 if win else None,
                "holdout_cells": 36 if win else 0,
                "budget_ms": BUDGETS[arm],
                "receipt_verified": True,
            })
    ledger = {"schema": RESULT_SCHEMA, "solver_source_commit": COMMIT,
              "preregistration_sha256": None,
              "public_manifest_sha256": digest(PUBLIC_MANIFEST), "results": rows}
    return metadata, ledger


def test_preregistration_freezes_source_and_is_non_overwriting(tmp_path):
    p = plan(tmp_path)
    assert p["solver_source_commit"] == COMMIT
    assert p["third_party_blind_study_completed"] is False
    with pytest.raises(FileExistsError):
        preregister(COMMIT, "a" * 64, tmp_path / "prereg.json")


@pytest.mark.parametrize("source, lock", [
    ("short", "a" * 64), (COMMIT, "short"), (COMMIT, "z" * 64),
])
def test_preregistration_rejects_invalid_hashes(tmp_path, source, lock):
    with pytest.raises(ValueError):
        preregister(source, lock, tmp_path / "x.json")


def test_100_public_commitments_validate_without_private_labels(tmp_path):
    result = check_public_panel(plan(tmp_path), *panel(tmp_path)[::-1])
    assert result["tasks_validated"] == 100
    assert result["private_labels_read"] is False
    assert result["external_blind_verified"] is False


def test_public_tampering_rejected(tmp_path):
    p = plan(tmp_path)
    root, manifest = panel(tmp_path)
    path = root / "internal_000.json"
    doc = read(path)
    doc["train"][0][2] = (doc["train"][0][2] + 1) % 10
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="missing/modified"):
        check_public_panel(p, manifest, root)


def test_private_leakage_rejected_even_with_matching_file_hash(tmp_path):
    p = plan(tmp_path)
    root, manifest = panel(tmp_path)
    path = root / "internal_000.json"
    doc = read(path)
    doc["holdout"] = [[6, 7, 9]]
    write_path = root / "temp.json"
    write_new(write_path, doc)
    path.write_bytes(write_path.read_bytes())
    write_path.unlink()
    manifest["tasks"][0]["public_sha256"] = file_sha(path)
    with pytest.raises(ValueError, match="private label"):
        check_public_panel(p, manifest, root)


def test_summary_paired_mcnemar_and_full_denominator(tmp_path):
    meta, ledger = scores()
    result = summarize(plan(tmp_path), meta, {**ledger, "preregistration_sha256": digest(plan(tmp_path))}, PUBLIC_MANIFEST)
    assert result["tasks"] == 100
    assert result["negative_controls"] == 25
    assert result["methods"]["frozen_portfolio"]["exact_success"] == 20
    assert result["methods"]["v3726_gate"]["exact_success"] == 10
    assert result["discordant_portfolio_only"] == 10
    assert result["discordant_gate_only"] == 0
    assert result["exact_mcnemar_two_sided_p"] == pytest.approx(2 / 1024)
    assert result["external_blind_verified"] is False


def test_missing_rows_retained_as_failures(tmp_path):
    meta, ledger = scores()
    ledger["results"] = [x for x in ledger["results"]
                         if not (x["arm"] == "frozen_portfolio" and x["task_id"] == "internal_025")]
    result = summarize(plan(tmp_path), meta, {**ledger, "preregistration_sha256": digest(plan(tmp_path))}, PUBLIC_MANIFEST)
    assert result["methods"]["frozen_portfolio"]["missing_submissions"] == 1
    assert result["methods"]["frozen_portfolio"]["exact_success"] == 19


def test_unequal_budget_rejected(tmp_path):
    meta, ledger = scores()
    ledger["results"][0]["budget_ms"] = 5000
    with pytest.raises(ValueError, match="unequal"):
        summarize(plan(tmp_path), meta, {**ledger, "preregistration_sha256": digest(plan(tmp_path))}, PUBLIC_MANIFEST)


def test_unverified_receipt_rejected(tmp_path):
    meta, ledger = scores()
    ledger["results"][0]["receipt_verified"] = False
    with pytest.raises(ValueError, match="unverified"):
        summarize(plan(tmp_path), meta, {**ledger, "preregistration_sha256": digest(plan(tmp_path))}, PUBLIC_MANIFEST)


def test_changed_commit_rejected(tmp_path):
    meta, ledger = scores()
    ledger["solver_source_commit"] = "d" * 40
    with pytest.raises(ValueError, match="solver"):
        summarize(plan(tmp_path), meta, {**ledger, "preregistration_sha256": digest(plan(tmp_path))}, PUBLIC_MANIFEST)


def test_insufficient_negative_controls_rejected(tmp_path):
    meta, ledger = scores()
    meta["categories"]["internal_024"] = "structured"
    with pytest.raises(ValueError, match="negative"):
        summarize(plan(tmp_path), meta, {**ledger, "preregistration_sha256": digest(plan(tmp_path))}, PUBLIC_MANIFEST)


def test_duplicate_score_rejected(tmp_path):
    meta, ledger = scores()
    ledger["results"].append(dict(ledger["results"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        summarize(plan(tmp_path), meta, {**ledger, "preregistration_sha256": digest(plan(tmp_path))}, PUBLIC_MANIFEST)


def test_failures_do_not_carry_hidden_labels(tmp_path):
    meta, ledger = scores()
    ledger["results"][0]["holdout_errors"] = 20
    with pytest.raises(ValueError, match="cannot include scored"):
        summarize(plan(tmp_path), meta, {**ledger, "preregistration_sha256": digest(plan(tmp_path))}, PUBLIC_MANIFEST)


def test_invalid_public_duplicate_coordinate_rejected(tmp_path):
    p = plan(tmp_path)
    root, manifest = panel(tmp_path)
    path = root / "internal_000.json"
    doc = read(path)
    doc["validation"][0][:2] = doc["train"][0][:2]
    doc["protocol_sha256"] = digest({k: v for k, v in doc.items() if k != "protocol_sha256"})
    path.write_text(json.dumps(doc), encoding="utf-8")
    manifest["tasks"][0]["public_sha256"] = file_sha(path)
    with pytest.raises(ValueError, match="overlap"):
        check_public_panel(p, manifest, root)


def test_manifest_binding_rejects_different_task_set(tmp_path):
    meta, ledger = scores()
    wrong = {**PUBLIC_MANIFEST, "tasks": list(PUBLIC_MANIFEST["tasks"])}
    wrong["tasks"][0] = {"task_id": "another_task", "public_sha256": "b"*64}
    ledger["preregistration_sha256"] = digest(plan(tmp_path))
    ledger["public_manifest_sha256"] = digest(wrong)
    with pytest.raises(ValueError, match="exactly match"):
        summarize(plan(tmp_path), meta, ledger, wrong)


def test_prereg_hash_mismatch_fails_closed(tmp_path):
    meta, ledger = scores()
    ledger["preregistration_sha256"] = "c"*64
    with pytest.raises(ValueError, match="preregistration"):
        summarize(plan(tmp_path), meta, ledger, PUBLIC_MANIFEST)


@pytest.mark.parametrize("name,new_value", [
    ("primary_endpoint", "any cell correct"),
    ("pairwise_test", "one-sided z-test"),
    ("confidence_interval", "none"),
    ("portfolio_budget_rule", "two subprocesses each 10000ms"),
    ("non_successes", ["FAILED"]),
    ("trusted_external_timestamp_verified", True),
    ("issuer_independence_verified", 0),
    ("min_negative_controls", 24),
])
def test_protocol_precommitment_rejects_changed_science(tmp_path, name, new_value):
    p = copy.deepcopy(plan(tmp_path))
    p[name] = new_value
    with pytest.raises(ValueError, match="protocol constraints changed"):
        plan_checked(p)
