"""V3.7.43: multi-window same-K PL5 filter ledger with chained evidence.

A retrospective synthetic pilot extending the V3.7.42 freeze/evaluate contract.
For each issue, the candidate builders receive ONLY the earlier prefix; full
candidate sets are hashed and verified before that issue's observation is
consulted. A chained audit detects omission/reordering/tampering of a report,
but is not independent trusted timing or public historical authentication.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np

from .affine_recurrence_filters_v3739 import recurrence_keep_masks
from .digit_structure_v3737 import DOMAIN
from .engine import select_numbers
from .filter_fair_ledger_v3742 import freeze_panel, evaluate_panel, verify_panel
from .legacy_filter_matrix_v3740 import _synthetic_records
from .pattern_rules import Configuration
from .probability_ranker import rank_target_snapshot_v3717

SCHEMA = "pl5-fair-filter-longitudinal-v3743-1"
METHODS = (
    "legacy_ensemble_k100", "legacy_pairwise_k100",
    "legacy_positional_k100", "legacy_rank_k100",
    "modular_recurrence_k100", "uniform_control_k100",
)
WINDOWS = 24
K = 100


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf8")


def _digest(value: object) -> str:
    return sha256(_canonical(value)).hexdigest()


def _identities(numbers: object) -> list[str]:
    if isinstance(numbers, np.ndarray):
        numbers = numbers.tolist()
    return sorted(f"{int(v):05d}" for v in numbers)


def _recurrence_ids() -> list[str]:
    bits = (1 << DOMAIN) - 1
    for mask in recurrence_keep_masks():
        bits &= mask
    result = []
    while bits:
        lowest = bits & -bits
        result.append(f"{lowest.bit_length() - 1:05d}")
        bits ^= lowest
    if len(result) != K:
        raise AssertionError("structural K=100 contract drift")
    return result


def frozen_method_ids(history: list[str], *, index: int) -> dict[str, list[str]]:
    """Return six complete identity sets from earlier rows, no target input."""
    if len(history) < 40 or type(index) is not int or index < len(history):
        raise ValueError("need a valid chronological past-only prefix")
    config = Configuration(
        indicators=("sum", "span", "digit_5"),
        transforms=("raw",), patterns=("constant", "arithmetic", "period2"),
        windows=(3, 4), min_keep=1000, max_total_remove=0.9,
        max_rules=25,
    )
    data = {}
    for method in ("positional", "pairwise", "ensemble"):
        picks = select_numbers(
            history, count=K, model=method,
            seed=374300 + 31 * index + {"positional": 0, "pairwise": 1, "ensemble": 2}[method],
            use_gate=False,
        ).numbers
        data[f"legacy_{method}_k100"] = _identities(picks)
    ranking = rank_target_snapshot_v3717(history, config)
    data["legacy_rank_k100"] = _identities(ranking.order[:K])
    data["modular_recurrence_k100"] = _recurrence_ids()
    data["uniform_control_k100"] = _identities(
        np.random.default_rng(374300 + 31 * index + 7).choice(DOMAIN, K, replace=False)
    )
    if set(data) != set(METHODS) or any(len(v) != K or len(set(v)) != K for v in data.values()):
        raise AssertionError("method availability, uniqueness or equal-budget drift")
    return data


def freeze_one(history: list[tuple[str, str]], next_issue: str,
               *, index: int) -> dict:
    """One issue-specific snapshot: no future observation value argument."""
    if not history or int(history[-1][0]) >= int(next_issue):
        raise ValueError("future window already entered the frozen prefix")
    numbers = [number for _, number in history]
    candidates = frozen_method_ids(numbers, index=index)
    module_root = Path(__file__).resolve().parent
    source_modules = {
        "legacy_ensemble_k100": "engine.py",
        "legacy_pairwise_k100": "engine.py",
        "legacy_positional_k100": "engine.py",
        "legacy_rank_k100": "probability_ranker.py",
        "modular_recurrence_k100": "affine_recurrence_filters_v3739.py",
        "uniform_control_k100": "filter_fair_longitudinal_v3743.py",
    }
    methods = {}
    for name in METHODS:
        implementation = (module_root / source_modules[name]).read_bytes()
        methods[name] = {
            "candidates": candidates[name],
            "version_sha256": sha256(implementation).hexdigest(),
            "rule_parameters_sha256": _digest({
                "method": name, "seed_base": 374300, "index": index,
                "candidate_budget": K, "gate": False,
                "numpy": np.__version__,
                "config": ("fixed_3_indicator_rules" if name == "legacy_rank_k100"
                           else "fixed_initial_math" if name == "modular_recurrence_k100"
                           else "frozen_model"),
            }),
        }
    record = freeze_panel(
        evaluation_issue=next_issue,
        last_training_issue=history[-1][0],
        training_data_sha256=_digest(history),
        methods=methods,
        evidence_class="INTERNAL_SYNTHETIC",
    )
    verify_panel(record)
    return record


def _signature(record: dict, previous: str) -> str:
    return _digest({
        "previous": previous, "panel": record["panel"],
        "settlement": record["settlement"],
    })


def run_longitudinal(*, windows: int = WINDOWS) -> dict:
    """Complete fixed-seed synthetic retrospective pilot, all windows kept."""
    if type(windows) is not int or not 1 <= windows <= WINDOWS:
        raise ValueError("synthetic pilot permits 1..24 most recent windows")
    records, meta = _synthetic_records()
    if len(records) < 40 + windows:
        raise ValueError("not enough synthetic prefix data")
    chain = "0" * 64
    reports = []
    for index in range(len(records) - windows, len(records)):
        prefix = records[:index]
        target_issue = records[index][0]
        panel = freeze_one(prefix, target_issue, index=index)
        # Only after freeze_one returns can the test observation be supplied.
        settled = evaluate_panel(
            panel, evaluation_issue=target_issue,
            observed_id=records[index][1],
            observation_source_sha256=_digest(records[index]),
            source_classification="INTERNAL_SYNTHETIC",
        )
        report = {
            "issue": target_issue,
            "panel": panel,
            "settlement": settled,
            "previous_chain_sha256": chain,
        }
        chain = _signature(report, chain)
        report["chain_sha256"] = chain
        reports.append(report)
    summary = []
    for name in METHODS:
        observations = [
            next(x for x in r["settlement"]["results"] if x["method"] == name)
            for r in reports
        ]
        summary.append({
            "method": name,
            "evaluations": windows,
            "retained_per_issue": K,
            "synthetic_contained": sum(int(x["retrospective_containment"]) for x in observations),
            "synthetic_false_excluded": sum(not x["retrospective_containment"] for x in observations),
            "sum_candidate_budget": K * windows,
            "retained_fraction": {"numerator": K, "denominator": DOMAIN},
        })
    result = {
        "schema": SCHEMA,
        "evidence_class": "INTERNAL_SYNTHETIC",
        "dataset_path": "data/synthetic_demo.csv",
        "dataset_raw_sha256": meta["source_sha256"],
        "number_of_evaluation_windows": windows,
        "warmup_before_first_window": len(records) - windows,
        "candidate_budget_each_method_each_window": K,
        "method_order": list(METHODS),
        "records": reports,
        "summary": summary,
        "final_chain_sha256": chain,
        "external_timestamp_attestation": False,
        "actual_history_authenticated": False,
        "independent_external_holdout": False,
        "statistical_advantage_claim": False,
    }
    verify_longitudinal(result)
    return result


def verify_longitudinal(report: object) -> None:
    if not isinstance(report, dict) or set(report) != {
        "schema", "evidence_class", "dataset_path", "dataset_raw_sha256",
        "number_of_evaluation_windows", "warmup_before_first_window",
        "candidate_budget_each_method_each_window", "method_order",
        "records", "summary", "final_chain_sha256",
        "external_timestamp_attestation", "actual_history_authenticated",
        "independent_external_holdout", "statistical_advantage_claim",
    }:
        raise ValueError("invalid longitudinal report envelope")
    if (report["schema"] != SCHEMA or report["evidence_class"] != "INTERNAL_SYNTHETIC"
            or report["method_order"] != list(METHODS)
            or type(report["number_of_evaluation_windows"]) is not int
            or len(report["records"]) != report["number_of_evaluation_windows"]
            or report["candidate_budget_each_method_each_window"] != K
            or any(report[k] is not False for k in (
                "external_timestamp_attestation", "actual_history_authenticated",
                "independent_external_holdout", "statistical_advantage_claim"
            ))):
        raise ValueError("invalid longitudinal protocol")
    chain = "0" * 64
    issues = []
    observed = {name: 0 for name in METHODS}
    for record in report["records"]:
        if not isinstance(record, dict) or set(record) != {
            "issue", "panel", "settlement", "previous_chain_sha256", "chain_sha256"
        }:
            raise ValueError("invalid chained record")
        if record["previous_chain_sha256"] != chain:
            raise ValueError("missing/reordered experiment record")
        p = verify_panel(record["panel"])
        s = record["settlement"]
        if (record["issue"] != p["evaluation_issue"] or s["evaluation_issue"] != p["evaluation_issue"]
                or s["frozen_payload_sha256"] != record["panel"]["payload_sha256"]
                or s["source_classification"] != "INTERNAL_SYNTHETIC"
                or type(s.get("observed_id")) is not str
                or len(s["observed_id"]) != 5 or not s["observed_id"].isascii()
                or not s["observed_id"].isdigit()
                or s["external_timestamp_attested"] is not False
                or [m["method"] for m in p["methods"]] != list(METHODS)
                or [m["method"] for m in s["results"]] != list(METHODS)
                or any(m["candidate_count"] != K for m in p["methods"])
                or any(m["candidate_count"] != K for m in s["results"])):
            raise ValueError("inconsistent frozen/evaluated method panel")
        issues.append(int(record["issue"]))
        for method, row in zip(p["methods"], s["results"]):
            if (type(row["retrospective_containment"]) is not bool
                    or row["retrospective_containment"]
                    != (s["observed_id"] in method["candidate_ids"])
                    or row["candidate_bitmap_sha256"] != method["candidate_bitmap_sha256"]
                    or row["retained_ratio_numerator"] != K
                    or row["retained_ratio_denominator"] != DOMAIN):
                raise ValueError("retrospective containment not reproducible from frozen IDs")
            observed[row["method"]] += int(row["retrospective_containment"])
        new = _signature(record, chain)
        if new != record["chain_sha256"]:
            raise ValueError("chained record digest mismatch")
        chain = new
    if issues != sorted(set(issues)) or chain != report["final_chain_sha256"]:
        raise ValueError("duplicate/out-of-order issues or final digest mismatch")
    for row in report["summary"]:
        if (row["method"] not in observed or row["evaluations"] != len(issues)
                or row["retained_per_issue"] != K
                or row["synthetic_contained"] != observed[row["method"]]
                or row["synthetic_false_excluded"] != len(issues) - observed[row["method"]]):
            raise ValueError("aggregate summary mismatch")
    if len(report["summary"]) != len(METHODS):
        raise ValueError("missing method from aggregate")



def structural_overlap_diagnostics(report: dict) -> dict:
    """Exact member overlap between methods and adjacent windows at K=100.

    These metrics remain useful even when no synthetic evaluation record
    belongs to any K=100 subset; no outcome values enter the calculation.
    """
    verify_longitudinal(report)
    views = []
    for record in report["records"]:
        views.append({
            arm["method"]: set(arm["candidate_ids"])
            for arm in record["panel"]["payload"]["methods"]
        })
    unions = [len(set().union(*snapshot.values())) for snapshot in views]
    pairs = []
    for i, left in enumerate(METHODS):
        for right in METHODS[i + 1:]:
            total = sum(len(snapshot[left] & snapshot[right]) for snapshot in views)
            pairs.append({
                "left": left, "right": right,
                "total_common_ids_across_windows": total,
                "mean_common_ids_numerator": total,
                "mean_common_ids_denominator": len(views),
                "identical_mask_windows": sum(snapshot[left] == snapshot[right]
                                              for snapshot in views),
            })
    changes = []
    for name in METHODS:
        common = sum(len(a[name] & b[name]) for a, b in zip(views, views[1:]))
        changes.append({
            "method": name,
            "adjacent_window_pairs": max(0, len(views) - 1),
            "common_ids_across_adjacent_windows": common,
            "mean_common_ids_numerator": common,
            "mean_common_ids_denominator": max(1, len(views) - 1),
        })
    return {
        "union_per_window": unions,
        "mean_union_size_numerator": sum(unions),
        "mean_union_size_denominator": len(views),
        "method_pairs": pairs,
        "within_method_adjacent_window_membership": changes,
        "identity_overlap_only": True,
    }


def summary_view(report: dict) -> dict:
    verify_longitudinal(report)
    return {
        "schema": report["schema"],
        "dataset_raw_sha256": report["dataset_raw_sha256"],
        "method_count": len(METHODS),
        "windows": report["number_of_evaluation_windows"],
        "K": K,
        "chain_sha256": report["final_chain_sha256"],
        "summary": report["summary"],
        "structural_overlap_diagnostics": structural_overlap_diagnostics(report),
        "evidence": "INTERNAL_SYNTHETIC_DEVELOPMENT",
        "limitations": [
            "All rows are synthetic; repeated inspection makes this a development-only record.",
            "Content hashes check consistency, not the time or original authorship of an experiment.",
            "The same finite K means identical structural budget, not equal runtime.",
            "A small count of retained synthetic observations cannot establish comparative superiority.",
        ],
    }


def main() -> None:
    """Single bounded internal demo run with complete immutable JSON evidence."""
    import argparse
    parser = argparse.ArgumentParser(description="PL5 frozen K=100 longitudinal engineering audit")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--windows", type=int, default=WINDOWS)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("will not overwrite existing evidence")
    report = run_longitudinal(windows=args.windows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True,
                         indent=2, allow_nan=False) + "\n"
    args.output.write_text(encoded, encoding="utf8")
    print(json.dumps({
        "output": str(args.output),
        "file_sha256": sha256(encoded.encode("utf8")).hexdigest(),
        **summary_view(report),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
