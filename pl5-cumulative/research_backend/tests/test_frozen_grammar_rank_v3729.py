"""Finite-field feasibility oracle cross-checks frozen V25/V26 fitting.

All data here is developer-authored, freshly synthetic and PUBLIC.
No AI100 private labels or frozen model logic is modified by this test.
"""
from __future__ import annotations

import numpy as np
import pytest

from pailie5.structure_search_v372 import CellDataset
from pailie5.open_grammar_v3725 import fit as fit25
from pailie5.gate_induction_v3726 import fit as fit26
from research_frozen_grammar_rank_v3729 import (
    feasibility_certificate, rank_prime, rank_audit, read_public_train, SCHEMA,
)


def training(kind):
    a, b = np.indices((10, 10), dtype=np.int64)
    a, b = a.flatten(), b.flatten()
    if kind == "linear":
        labels = (3 * a + 2 * b + 5) % 10
    elif kind == "piecewise_equal":
        labels = np.where(a == b, a * b + 4, np.bitwise_xor(a, b) + 3) % 10
    elif kind == "random_table":
        labels = np.random.default_rng(753122).integers(0, 10, 100)
    else:
        raise ValueError(kind)
    sample = np.random.default_rng(20261123).permutation(100)[:48]
    return CellDataset(tuple((int(a[k]), int(b[k]), int(labels[k])) for k in sample))


def test_exact_mod2_5_rank_oracle():
    x = np.array([[1, 0], [0, 1], [1, 1]], dtype=np.int64)
    y = np.array([7, 6, 3], dtype=np.int64)
    evidence = feasibility_certificate(x, y)
    assert evidence["exact_mod10_training_fit_exists"]
    assert all(not p["inconsistent"] for p in evidence["ranks_mod_primes"].values())
    # Mod 2 has equal labels (0,0) and is consistent; modulo 5 is not.
    x2 = np.array([[2], [2]], dtype=np.int64)
    y2 = np.array([2, 4], dtype=np.int64)
    evidence2 = feasibility_certificate(x2, y2)
    assert not evidence2["exact_mod10_training_fit_exists"]
    assert evidence2["ranks_mod_primes"]["2"]["inconsistent"] is False
    assert evidence2["ranks_mod_primes"]["5"]["inconsistent"] is True
    with pytest.raises(ValueError):
        rank_prime(x, 7)


@pytest.mark.parametrize("kind", ["linear", "piecewise_equal", "random_table"])
def test_feasibility_agrees_with_frozen_fit_stage_by_stage(kind, tmp_path):
    observed = training(kind)
    cert = rank_audit(observed)
    v25 = fit25(observed, tmp_path / (kind + "_v25"))
    v26 = fit26(observed, tmp_path / (kind + "_v26"))
    assert cert["schema"] == SCHEMA
    assert len(cert["v3725_stages"]) == 4
    assert len(cert["v3726_predicates"]) == 26
    assert [x["exact_mod10_training_fit_exists"] for x in cert["v3725_stages"]] == [
        x["exact_train_fit"] for x in v25["stage_trace"]]
    assert [x["exact_mod10_training_fit_exists"] for x in cert["v3726_predicates"]] == [
        x["exact_train_fit"] for x in v26["trace"]]
    assert cert["v3725_any_train_fit"] == bool(v25["exact_fit_tables"])
    assert cert["v3726_any_train_fit"] == bool(v26["exact_fit_tables"])
    assert cert["holdout_labels_seen"] is False
    assert cert["validation_labels_seen"] is False
    assert cert["external_blind_verified"] is False
    if kind == "linear":
        assert cert["v3725_any_train_fit"] and cert["v3726_any_train_fit"]
    if kind == "piecewise_equal":
        assert cert["v3726_any_train_fit"]
    if kind == "random_table":
        assert not cert["v3725_any_train_fit"]
        assert not cert["v3726_any_train_fit"]


def test_tampered_and_nonpublic_task_rejected(tmp_path):
    file = tmp_path / "public.json"
    file.write_text('{"schema":"anything","train":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="public challenge"):
        read_public_train(file)
