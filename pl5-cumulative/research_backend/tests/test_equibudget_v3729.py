"""V3.7.29 internal seeded pilot for separate 10s-vs-(5s+5s) trials.

NOT an external blind test: the developer creates and knows the answer table.
"""
import json
from pathlib import Path

import pytest

from benchmark_hard_budget_v3727 import task, SEEDS
from research_open_grammar_v3725 import prepare
from research_signed_blind_v3728 import keygen
from research_equibudget_v3729 import (
    issue_pair, freeze_pair, settle_pair, ATT10, ATT5, STANDALONE, PORTFOLIO,
)

BACKEND = Path(__file__).resolve().parents[1]


def fixture(tmp_path):
    private_dir = tmp_path / "secrets"
    private_dir.mkdir()
    keys = {}
    for role in ("issuer", "solver", "grader"):
        keys[role] = (private_dir / f"{role}.key", tmp_path / f"{role}.pub")
        keygen(*keys[role])
    task_file = tmp_path / "developer_task.json"
    task_file.write_text(json.dumps(task("equal_gate", SEEDS[0])), encoding="utf-8")
    prepare(task_file, tmp_path / "public", private_dir / "holdout")
    public = tmp_path / "public" / "public_challenge.json"
    secret = private_dir / "holdout" / "private_challenge.json"
    return public, secret, keys


def test_equal_budget_signed_freeze_both_before_private_grading(tmp_path):
    public, private, keys = fixture(tmp_path)
    iss = issue_pair(public, BACKEND, *keys["issuer"], tmp_path / "issuer_receipts")
    assert iss["budgets_ms"] == {"standalone": 10000, "portfolio_each": 5000}
    frozen = freeze_pair(public, BACKEND, tmp_path / "issuer_receipts",
                         keys["issuer"][1], *keys["solver"], tmp_path / "solver")
    assert frozen["stage"] == "FROZEN_BOTH_BEFORE_GRADING"
    assert (tmp_path / "solver" / STANDALONE / "solver_signed_receipt.json").exists()
    assert (tmp_path / "solver" / PORTFOLIO / "solver_signed_receipt.json").exists()
    assert not (tmp_path / "solver" / STANDALONE / "score.json").exists()
    assert not (tmp_path / "solver" / PORTFOLIO / "score.json").exists()
    assert not private.is_relative_to(tmp_path / "solver")
    result = settle_pair(public, private, BACKEND, tmp_path / "issuer_receipts",
                         keys["issuer"][1], keys["solver"][1],
                         *keys["grader"], tmp_path / "solver")
    assert result["stage"] == "SIGNED_GRADED"
    assert result["external_blind_verified"] is False
    assert set(x["arm"] for x in result["rows"]) == {
        "v3725_ring", "v3726_gate", "frozen_portfolio"}
    assert all(x["budget_ms"] == 10000 and x["receipt_verified"] is True
               for x in result["rows"])
    tele = json.loads((tmp_path / "solver" / "equal_budget_telemetry.json").read_text())
    assert len(tele["arms"]["frozen_portfolio"]["observed_component_wall_ms"]) == 2
    assert tele["trusted_timestamp_verified"] is False
    with pytest.raises(FileExistsError):
        settle_pair(public, private, BACKEND, tmp_path / "issuer_receipts",
                    keys["issuer"][1], keys["solver"][1],
                    *keys["grader"], tmp_path / "solver")


def test_issue_is_non_overwriting(tmp_path):
    public, _, keys = fixture(tmp_path)
    out = tmp_path / "issuer_receipts"
    issue_pair(public, BACKEND, *keys["issuer"], out)
    assert (out / ATT10).exists() and (out / ATT5).exists()
    with pytest.raises(FileExistsError):
        issue_pair(public, BACKEND, *keys["issuer"], out)
