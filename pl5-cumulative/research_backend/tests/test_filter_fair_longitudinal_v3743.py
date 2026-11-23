"""V3.7.43: longitudinal full-membership exact verification and stability."""
from copy import deepcopy
from functools import lru_cache

import pytest

from pailie5.filter_fair_longitudinal_v3743 import (
    K, METHODS, freeze_one, run_longitudinal, summary_view, verify_longitudinal
)
from pailie5.filter_fair_ledger_v3742 import verify_panel


@lru_cache(maxsize=2)
def small():
    return run_longitudinal(windows=4)


def test_four_chronological_windows_all_six_legacy_arms_equal_k_and_reproducible():
    r = small()
    assert r == run_longitudinal(windows=4)
    verify_longitudinal(r)
    summary = summary_view(r)
    assert summary["windows"] == 4 and summary["K"] == K == 100
    assert summary["method_count"] == len(METHODS) == 6
    assert [row["method"] for row in summary["summary"]] == list(METHODS)
    assert all(row["retained_per_issue"] == 100
               and row["evaluations"] == 4
               and row["synthetic_contained"] + row["synthetic_false_excluded"] == 4
               for row in summary["summary"])
    assert not r["actual_history_authenticated"]
    assert not r["external_timestamp_attestation"]
    assert not r["independent_external_holdout"]
    assert len(r["final_chain_sha256"]) == 64


def test_each_settlement_recomputed_by_actual_full_frozen_candidate_list():
    r = small()
    for record in r["records"]:
        payload = verify_panel(record["panel"])
        target = record["settlement"]["observed_id"]
        assert all(
            (target in m["candidate_ids"]) == s["retrospective_containment"]
            for m, s in zip(payload["methods"], record["settlement"]["results"])
        )
        assert all(m["candidate_count"] == 100 for m in payload["methods"])
    assert [int(x["issue"]) for x in r["records"]] == [997, 998, 999, 1000]


def test_chained_ledger_detects_reordered_deleted_and_tampered_records():
    baseline = small()
    for change in (
        lambda d: d["records"].reverse(),
        lambda d: d["records"].pop(1),
        lambda d: d["records"][0]["settlement"]["results"][0].update(
            {"retrospective_containment": True if not d["records"][0]["settlement"]["results"][0]["retrospective_containment"] else False}
        ),
        lambda d: d["records"][0]["panel"]["payload"]["methods"][0]["candidate_ids"].append("99999"),
        lambda d: d["records"][0]["settlement"].update({"observed_id": "99999"}),
        lambda d: d["summary"][0].update({"synthetic_contained": 999}),
    ):
        modified = deepcopy(baseline)
        change(modified)
        with pytest.raises(ValueError):
            verify_longitudinal(modified)


def test_future_only_changes_cannot_change_earlier_frozen_snapshot():
    past = [(f"{i:06d}", f"{i * 703 % 100000:05d}") for i in range(1, 42)]
    frozen = freeze_one(past, "000042", index=41)
    a = freeze_one(list(past), "000042", index=41)
    assert frozen == a
    assert "61520" not in str(frozen)  # unrelated reserved synthetic record
    assert frozen["payload"]["last_training_issue"] == "000041"
    with pytest.raises(ValueError):
        freeze_one(past + [("000042", "61520")], "000042", index=42)


@pytest.mark.parametrize("bad", [0, -1, True, 25, "4"])
def test_bad_window_protocol_rejected(bad):
    with pytest.raises(ValueError):
        run_longitudinal(windows=bad)
