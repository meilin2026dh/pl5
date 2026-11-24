"""V3.7.42 robust freeze-before-retrospective-validation test suite."""
import copy
from hashlib import sha256
import json

import pytest

from pailie5.filter_fair_ledger_v3742 import (
    freeze_panel, evaluate_panel, verify_panel,
)
from pailie5.filter_fair_cli_v3742 import (
    freeze_training_csv, evaluate_record_file, _save_new,
)


def _digest(data=b"one training-only sequence") -> str:
    return sha256(data).hexdigest()


def _method(ids, *, version=None):
    return {
        "candidates": list(ids),
        "version_sha256": version or _digest(b"source-code-v1"),
        "rule_parameters_sha256": _digest(b"frozen-parameters"),
    }


def _seal(**kwargs):
    return freeze_panel(
        evaluation_issue="000043",
        last_training_issue="000042",
        training_data_sha256=_digest(),
        methods={
            "a": _method(["00000", "00001", "00200"]),
            "b": _method(["00002", "00003", "00200"]),
            "c": _method(["99999"]),
        },
        **kwargs,
    )


def test_frozen_payload_is_deterministic_content_addressed_and_full_membership():
    s = _seal()
    assert s == _seal()
    record = verify_panel(s)
    assert record["evaluation_issue"] == "000043"
    assert [m["candidate_count"] for m in record["methods"]] == [3, 3, 1]
    assert len({m["candidate_bitmap_sha256"] for m in record["methods"]}) == 3
    assert s["timestamp_attestation"] == "NONE_CONTENT_HASH_ONLY"
    assert "observed_id" not in json.dumps(s)


def test_settlement_keeps_equal_k_groups_and_no_invented_timestamps():
    s = _seal()
    result = evaluate_panel(
        s, evaluation_issue="000043", observed_id="00200",
        observation_source_sha256=_digest(b"separate evaluation record"),
        source_classification="INTERNAL_SYNTHETIC",
    )
    assert result["matched_budget_groups"] == {"3": ["a", "b"], "1": ["c"]}
    assert [x["retrospective_containment"] for x in result["results"]] == [
        True, True, False
    ]
    assert all(x["candidate_count"] == x["retained_ratio_numerator"]
               for x in result["results"])
    assert result["frozen_payload_sha256"] == s["payload_sha256"]
    assert not result["external_timestamp_attested"]
    assert not result["source_identity_authenticated_by_this_module"]


def test_after_freeze_tampering_and_fabrication_are_rejected():
    s = _seal()
    for altered in (
        lambda x: x["payload"]["methods"][0]["candidate_ids"].append("00010"),
        lambda x: x["payload"]["methods"][0].update({"candidate_count": 4}),
        lambda x: x["payload"].update({"unseen_future": "00001"}),
        lambda x: x.update({"timestamp_attestation": "TRUSTED"}),
        lambda x: x.update({"state": "SETTLED"}),
    ):
        t = copy.deepcopy(s)
        altered(t)
        with pytest.raises(ValueError):
            verify_panel(t)


def test_rehashed_tamper_does_not_evade_member_consistency():
    s = _seal()
    t = copy.deepcopy(s)
    t["payload"]["methods"][0]["candidate_ids"] = ["00000", "00001", "00002"]
    t["payload_sha256"] = _digest(
        json.dumps(t["payload"], ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")).encode("utf8")
    )
    with pytest.raises(ValueError, match="candidate proof"):
        verify_panel(t)


@pytest.mark.parametrize("ids", [
    ["001"], ["１２３４５"], ["00002", "00001"],
    ["00000", "00000"], [], ["12345", 12345],
])
def test_invalid_candidate_lists_are_rejected(ids):
    with pytest.raises(ValueError):
        freeze_panel(
            evaluation_issue="11", last_training_issue="10",
            training_data_sha256=_digest(),
            methods={"a": _method(ids), "b": _method(["00001"])},
        )


def test_future_issue_and_source_gates_are_strict():
    with pytest.raises(ValueError):
        freeze_panel(evaluation_issue="10", last_training_issue="10",
                     training_data_sha256=_digest(),
                     methods={"a": _method(["00001"]), "b": _method(["00002"])})
    s = _seal()
    with pytest.raises(ValueError):
        evaluate_panel(s, evaluation_issue="000044", observed_id="00001",
                       observation_source_sha256=_digest(),
                       source_classification="INTERNAL_SYNTHETIC")
    with pytest.raises(ValueError):
        evaluate_panel(s, evaluation_issue="000043", observed_id="00001",
                       observation_source_sha256=_digest(),
                       source_classification="CROSSCHECKED_HISTORICAL")
    with pytest.raises(ValueError):
        evaluate_panel(s, evaluation_issue="000043", observed_id="12",
                       observation_source_sha256=_digest(),
                       source_classification="INTERNAL_SYNTHETIC")


def _write_training_only(path):
    with path.open("x", encoding="utf8", newline="") as stream:
        stream.write("period,number\n")
        for i in range(1, 42):
            stream.write(f"{i:06d},{(10003*i) % 100000:05d}\n")


def test_real_existing_legacy_and_recurrence_adapters_sealed_then_evaluated(tmp_path):
    training = tmp_path / "training.csv"
    observation = tmp_path / "observation.csv"
    _write_training_only(training)
    seal = freeze_training_csv(training, evaluation_issue="000042")
    p = verify_panel(seal)
    assert len(p["methods"]) == 3
    assert [x["candidate_count"] for x in p["methods"]] == [100, 100, 100]
    assert len({x["version_sha256"] for x in p["methods"]}) == 3
    assert p["last_training_issue"] == "000041"
    assert p["training_data_sha256"] == sha256(training.read_bytes()).hexdigest()
    _save_new(tmp_path / "frozen.json", seal)
    with pytest.raises(FileExistsError):
        _save_new(tmp_path / "frozen.json", seal)
    observation.write_text("period,number\n000042,01400\n", encoding="utf8")
    result = evaluate_record_file(seal, observation)
    assert result["evaluation_issue"] == "000042"
    assert result["matched_budget_groups"] == {
        "100": ["legacy_positional_k100", "recurrence_t3", "uniform_control_k100"]
    }
    assert result["source_classification"] == "INTERNAL_SYNTHETIC"
    assert result["full_candidate_memberships_verified"]
    assert result["statistical_significance_evaluated"] is False
    with pytest.raises(ValueError):
        observation.write_text("period,number\n000043,99999\n", encoding="utf8")
        evaluate_record_file(seal, observation)
