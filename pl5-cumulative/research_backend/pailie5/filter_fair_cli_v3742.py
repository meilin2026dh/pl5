"""V3.7.42 sealed-filter panel command line: independent freeze/evaluate actions.

Never let the freeze command read the evaluation record. Its input CSV holds
ONLY training rows. No GitHub write operations, notifications or web calls.
"""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from .affine_recurrence_filters_v3739 import recurrence_keep_masks
from .engine import select_numbers
from .filter_fair_ledger_v3742 import freeze_panel, evaluate_panel, verify_panel
from .number_validation import is_numeric_issue, is_five_digit_draw


def _save_new(path: Path, payload: dict) -> None:
    if path.exists():
        raise FileExistsError("refuse to overwrite a previous experiment record")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf8") as fh:
        json.dump(payload, fh, sort_keys=True, indent=2, ensure_ascii=False)
        fh.write("\n")


def _read_training(path: Path) -> tuple[list[tuple[str, str]], str]:
    raw = path.read_bytes()
    reader = csv.DictReader(raw.decode("utf8-sig").splitlines())
    if reader.fieldnames != ["period", "number"]:
        raise ValueError("training CSV needs period,number only")
    rows = [(r["period"], r["number"]) for r in reader]
    if (len(rows) < 20 or any(not is_numeric_issue(p) or not is_five_digit_draw(n)
                               for p, n in rows)
            or any(int(a[0]) >= int(b[0]) for a, b in zip(rows, rows[1:]))):
        raise ValueError("invalid or out-of-order training rows")
    return rows, sha256(raw).hexdigest()


def _from_bitset(bits: int) -> list[str]:
    rows = []
    while bits:
        low = bits & -bits
        number = low.bit_length() - 1
        rows.append(f"{number:05d}")
        bits ^= low
    return rows


def freeze_training_csv(path: Path, *, evaluation_issue: str) -> dict:
    rows, digest = _read_training(path)
    history = [number for _, number in rows]
    recurrence = recurrence_keep_masks()
    keep = recurrence[0] & recurrence[1] & recurrence[2]
    refs = {
        "recurrence_t3": _from_bitset(keep),
        "legacy_positional_k100": [
            f"{int(v):05d}" for v in sorted(select_numbers(
                history, count=100, model="positional",
                seed=3742, use_gate=False,
            ).numbers)
        ],
        "uniform_control_k100": [
            f"{int(v):05d}" for v in sorted(np.random.default_rng(
                3742).choice(100_000, size=100, replace=False))
        ],
    }
    methods = {}
    for name, ids in refs.items():
        version = sha256(("v3742|" + name).encode("ascii")).hexdigest()
        parameters = sha256((name + "|seed=3742|K=100").encode("ascii")).hexdigest()
        methods[name] = {
            "candidates": ids, "version_sha256": version,
            "rule_parameters_sha256": parameters,
        }
    record = freeze_panel(
        evaluation_issue=evaluation_issue,
        last_training_issue=rows[-1][0],
        training_data_sha256=digest,
        methods=methods,
        evidence_class="INTERNAL_SYNTHETIC",
    )
    verify_panel(record)
    return record


def evaluate_record_file(frozen: dict, observation_path: Path) -> dict:
    raw = observation_path.read_bytes()
    table = list(csv.DictReader(raw.decode("utf8-sig").splitlines()))
    if len(table) != 1 or set(table[0]) != {"period", "number"}:
        raise ValueError("observation must contain one period,number row")
    return evaluate_panel(
        frozen, evaluation_issue=table[0]["period"],
        observed_id=table[0]["number"],
        observation_source_sha256=sha256(raw).hexdigest(),
        source_classification="INTERNAL_SYNTHETIC",
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Separated PL5 filter ledger operations")
    subs = p.add_subparsers(dest="action", required=True)
    pre = subs.add_parser("freeze")
    pre.add_argument("--training-csv", required=True, type=Path)
    pre.add_argument("--evaluation-issue", required=True)
    pre.add_argument("--output", required=True, type=Path)
    post = subs.add_parser("evaluate")
    post.add_argument("--frozen", required=True, type=Path)
    post.add_argument("--observation-csv", required=True, type=Path)
    post.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    if args.action == "freeze":
        payload = freeze_training_csv(
            args.training_csv, evaluation_issue=args.evaluation_issue)
    else:
        payload = evaluate_record_file(
            json.loads(args.frozen.read_text(encoding="utf8")),
            args.observation_csv)
    _save_new(args.output, payload)
    print(json.dumps({
        "action": args.action, "output": str(args.output),
        "content_sha256": sha256(args.output.read_bytes()).hexdigest(),
        "evaluation_issue": (
            payload["payload"]["evaluation_issue"] if args.action == "freeze"
            else payload["evaluation_issue"]),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
