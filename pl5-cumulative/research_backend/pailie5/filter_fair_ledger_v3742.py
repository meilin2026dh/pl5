"""V3.7.42: hash-sealed, budget-matched PL5 filter research ledger.

Two separately invoked operations:
  1. freeze_panel: snapshot full candidate memberships and method versions
     BEFORE a reserved evaluation row is supplied to this function.
  2. evaluate_panel: verify the complete snapshot then record retrospective
     containment for a matching evaluation issue.

Uses no untrusted network access, external clocks, or mutable databases.
SHA256 binds contents; it is NOT a trusted timestamp or source attestation.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from .number_validation import is_five_digit_draw, is_numeric_issue

SCHEMA = "pl5-filter-fair-panel-v3742-1"
DOMAIN = 100_000
PAYLOAD_FIELDS = frozenset({
    "schema", "evaluation_issue", "last_training_issue",
    "training_data_sha256", "evidence_class", "methods",
})
METHOD_FIELDS = frozenset({
    "method", "version_sha256", "rule_parameters_sha256",
    "candidate_ids", "candidate_count", "candidate_bitmap_sha256",
})
HEX = frozenset("0123456789abcdef")


def _valid_digest(s: object) -> bool:
    return type(s) is str and len(s) == 64 and all(x in HEX for x in s)


def _hash(data: bytes) -> str:
    return sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf8")


def _candidate_digest(ids: tuple[str, ...]) -> str:
    bitmap = 0
    for candidate in ids:
        bitmap |= 1 << int(candidate)
    return _hash(bitmap.to_bytes((DOMAIN + 7) // 8, "little"))


def _candidate_ids(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError("candidate list must be nonempty")
    if len(raw) > DOMAIN or any(not is_five_digit_draw(x) for x in raw):
        raise ValueError("candidate IDs require exactly five ASCII digits")
    if tuple(sorted(raw)) != tuple(raw) or len(set(raw)) != len(raw):
        raise ValueError("candidate IDs must be sorted and unique")
    return tuple(raw)


def freeze_panel(
    *, evaluation_issue: str, last_training_issue: str,
    training_data_sha256: str, methods: Mapping[str, dict],
    evidence_class: str = "INTERNAL_SYNTHETIC",
) -> dict[str, Any]:
    """Freeze all candidate sets without receiving the evaluation outcome."""
    if (not is_numeric_issue(evaluation_issue)
            or not is_numeric_issue(last_training_issue)
            or int(last_training_issue) >= int(evaluation_issue)):
        raise ValueError("evaluation issue must follow the training window")
    if not _valid_digest(training_data_sha256):
        raise ValueError("training digest must be lowercase SHA256 hex")
    if evidence_class not in ("INTERNAL_SYNTHETIC", "CROSSCHECKED_HISTORICAL"):
        raise ValueError("source classification must be explicit")
    if (not isinstance(methods, Mapping) or len(methods) < 2
            or len(methods) > 60):
        raise ValueError("fair panel requires between 2 and 60 methods")
    normalized = []
    for name in sorted(methods):
        obj = methods[name]
        if (type(name) is not str or not name or not isinstance(obj, dict)
                or set(obj) != {"candidates", "version_sha256", "rule_parameters_sha256"}
                or not _valid_digest(obj["version_sha256"])
                or not _valid_digest(obj["rule_parameters_sha256"])):
            raise ValueError("method registration invalid")
        ids = _candidate_ids(obj["candidates"])
        normalized.append({
            "method": name, "version_sha256": obj["version_sha256"],
            "rule_parameters_sha256": obj["rule_parameters_sha256"],
            "candidate_ids": list(ids), "candidate_count": len(ids),
            "candidate_bitmap_sha256": _candidate_digest(ids),
        })
    payload = {
        "schema": SCHEMA,
        "evaluation_issue": evaluation_issue,
        "last_training_issue": last_training_issue,
        "training_data_sha256": training_data_sha256,
        "evidence_class": evidence_class,
        "methods": normalized,
    }
    return {
        "payload": payload,
        "payload_sha256": _hash(_canonical(payload)),
        "timestamp_attestation": "NONE_CONTENT_HASH_ONLY",
        "state": "FROZEN_AWAITING_RETROSPECTIVE_EVALUATION",
    }


def verify_panel(record: object) -> dict:
    """Fail closed on edits, bad membership, unknown fields and digest drift."""
    if (type(record) is not dict
            or set(record) != {"payload", "payload_sha256",
                               "timestamp_attestation", "state"}):
        raise ValueError("invalid frozen panel envelope")
    if (record["state"] != "FROZEN_AWAITING_RETROSPECTIVE_EVALUATION"
            or record["timestamp_attestation"] != "NONE_CONTENT_HASH_ONLY"
            or not _valid_digest(record["payload_sha256"])):
        raise ValueError("invalid frozen panel metadata")
    payload = record["payload"]
    if not isinstance(payload, dict) or set(payload) != PAYLOAD_FIELDS:
        raise ValueError("invalid frozen panel payload")
    if _hash(_canonical(payload)) != record["payload_sha256"]:
        raise ValueError("frozen panel digest mismatch")
    if (payload["schema"] != SCHEMA or not is_numeric_issue(payload["evaluation_issue"])
            or not is_numeric_issue(payload["last_training_issue"])
            or int(payload["last_training_issue"]) >= int(payload["evaluation_issue"])
            or not _valid_digest(payload["training_data_sha256"])
            or payload["evidence_class"] not in ("INTERNAL_SYNTHETIC", "CROSSCHECKED_HISTORICAL")
            or type(payload["methods"]) is not list
            or not 2 <= len(payload["methods"]) <= 60):
        raise ValueError("frozen panel protocol failure")
    names = []
    for arm in payload["methods"]:
        if not isinstance(arm, dict) or set(arm) != METHOD_FIELDS:
            raise ValueError("unknown method fields")
        ids = _candidate_ids(arm["candidate_ids"])
        if (type(arm["method"]) is not str or not arm["method"]
                or not _valid_digest(arm["version_sha256"])
                or not _valid_digest(arm["rule_parameters_sha256"])
                or type(arm["candidate_count"]) is not int
                or arm["candidate_count"] != len(ids)
                or arm["candidate_bitmap_sha256"] != _candidate_digest(ids)):
            raise ValueError("invalid method candidate proof")
        names.append(arm["method"])
    if names != sorted(set(names)):
        raise ValueError("method order and uniqueness invalid")
    return payload


def evaluate_panel(
    frozen: object, *, evaluation_issue: str, observed_id: str,
    observation_source_sha256: str, source_classification: str,
) -> dict:
    """Evaluate immutable candidates on ONE exact matching reserved issue.

    The observation is supplied only to this function. The resulting source
    classification is caller supplied, not independently authenticated.
    """
    payload = verify_panel(frozen)
    if evaluation_issue != payload["evaluation_issue"]:
        raise ValueError("evaluation issue differs from sealed target")
    if not is_five_digit_draw(observed_id):
        raise ValueError("observed identifier invalid")
    if not _valid_digest(observation_source_sha256):
        raise ValueError("observation source digest invalid")
    if source_classification != payload["evidence_class"]:
        raise ValueError("observation source classification does not match frozen panel")
    rows = []
    for arm in payload["methods"]:
        ids = arm["candidate_ids"]
        count = arm["candidate_count"]
        rows.append({
            "method": arm["method"],
            "candidate_count": count,
            "candidate_bitmap_sha256": arm["candidate_bitmap_sha256"],
            "retained_ratio_numerator": count,
            "retained_ratio_denominator": DOMAIN,
            "retrospective_containment": observed_id in ids,
        })
    groups = {}
    for row in rows:
        groups.setdefault(str(row["candidate_count"]), []).append(row["method"])
    return {
        "schema": "pl5-filter-fair-settlement-v3742-1",
        "frozen_payload_sha256": frozen["payload_sha256"],
        "evaluation_issue": evaluation_issue,
        "observation_source_sha256": observation_source_sha256,
        "source_classification": source_classification,
        "source_identity_authenticated_by_this_module": False,
        "external_timestamp_attested": False,
        "full_candidate_memberships_verified": True,
        "matched_budget_groups": groups,
        "results": rows,
        "statistical_significance_evaluated": False,
        "warning": "One historical record and content hashes cannot establish any general retention advantage.",
    }
