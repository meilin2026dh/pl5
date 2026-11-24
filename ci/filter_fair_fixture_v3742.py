"""Extract disjoint INTERNAL SYNTHETIC demo records for two CI jobs.

This utility is a *fixture splitter*, not an independent data custodian.
The first 41 rows are training, row 42 is evaluation. The freeze
process never receives the second file. Full fixture remains synthetic.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("training", "observation"), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("will not overwrite fixture")
    with args.input.open("r", encoding="utf8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != ["period", "number"]:
            raise ValueError("unexpected source columns")
        rows = list(reader)
    if len(rows) < 42 or rows[40]["period"] >= rows[41]["period"]:
        raise ValueError("synthetic row count or issue order invalid")
    selected = rows[:41] if args.mode == "training" else rows[41:42]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["period", "number"])
        writer.writeheader()
        writer.writerows(selected)
    print(f"fixture_mode={args.mode} rows={len(selected)}")
    if args.mode == "observation":
        print(f"evaluation_issue={selected[0]['period']}")


if __name__ == "__main__":
    main()
