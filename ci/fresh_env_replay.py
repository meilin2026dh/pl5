#!/usr/bin/env python3
"""PL5 clean-machine inventory and representative historical replay.

Only stored synthetic/internal experiments are replayed. Do not infer lottery
prediction advantage, external blind verification or user-PC installation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUM = ROOT / "pl5-cumulative"
BACKEND = CUM / "research_backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inventory() -> dict:
    manifest = ROOT / "archive/v3728/PL5_V3728_Public_Upload_Selected.csv"
    with manifest.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    failures = []
    seen = set()
    for row in rows:
        path = row["path"]
        if path in seen or ".." in Path(path).parts or Path(path).is_absolute():
            failures.append({"path": path, "issue": "duplicate/unsafe manifest path"})
            continue
        seen.add(path)
        f = CUM / path
        if not f.is_file():
            failures.append({"path": path, "issue": "missing"})
            continue
        if f.stat().st_size != int(row["size_bytes"]) or sha256(f) != row["sha256"].lower():
            failures.append({"path": path, "issue": "size or SHA256 mismatch"})
    files = subprocess.run(["git", "-c", "core.quotePath=false", "ls-files", "--", "pl5-cumulative/"],
                           cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
    count = len(files)
    # The V3.7.28 accepted main snapshot has 6,364 cumulative paths
    # (6,361 prior archive + 3 restored V3.7.19 records). Preserve that
    # original snapshot while allowing new tracked research files.
    accepted_main = "c0e38040ec5f389d6444e64b90e7adc42adfca62"
    original_paths = subprocess.run(
        ["git", "-c", "core.quotePath=false", "ls-tree", "-r", "--name-only",
         accepted_main, "--", "pl5-cumulative/"],
        cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout.splitlines()
    removed = sorted(set(original_paths) - set(files))
    if len(rows) != 5451 or len(seen) != 5451 or len(original_paths) != 6364:
        failures.append({"issue": "frozen archival baseline mismatch",
                         "manifest": len(rows), "unique": len(seen),
                         "accepted_main_cumulative": len(original_paths)})
    if removed:
        failures.append({"issue": "accepted baseline files removed", "paths": removed[:15]})
    # These 3 source records are new tracked files. The two CSVs were recovered
    # byte-for-byte from preexisting manifest SHA256; the provenance JSON is
    # explicitly identified as reconstructed rather than a byte-identical original.
    for filename, digest, size in (
        ('jiangsu_transcribed.csv', '6962260131f6f78072bb4b0ec95514ff8ec764e1d3a2048a275e06a24644b00e', 625),
        ('gansu_transcribed.csv', 'ca0c2ef7ff02dedc8d467a0ae1c829683339f7831911b520694cb6af7df9da26', 253),
    ):
        f = CUM / 'data' / 'official_transcriptions_v3719' / filename
        if not f.is_file() or f.stat().st_size != size or sha256(f) != digest:
            failures.append({'path': str(f), 'issue': 'restored official source SHA256 mismatch'})
    if failures:
        raise AssertionError(json.dumps(failures[:15], ensure_ascii=False))
    return {"manifest_files_verified": len(rows),
            "accepted_main_cumulative_files": len(original_paths),
            "tracked_cumulative_files": count,
            "new_cumulative_files": count - len(original_paths),
            "sha256_verified": True, "held_back_private_files_included": False}


def replay_bitmap() -> dict:
    from benchmark_bitmap_workflows_v3716 import run_benchmark
    results = {}
    for seed, filename in ((3716, "benchmark.json"), (3717, "benchmark_repeat.json")):
        expected = json.loads((CUM / "docs/v3716" / filename).read_text(encoding="utf-8"))
        actual = run_benchmark(repeats=1, seed=seed)
        if actual["data_source"]["sha256"] != expected["data_source"]["sha256"]:
            raise AssertionError(f"V3.7.16 seed {seed}: input data SHA256 differs")
        for workflow, old in expected["workflows"].items():
            now = actual["workflows"][workflow]
            if now["digest_sha256"] != old["digest_sha256"] or not now["equivalence"]["exact"]:
                raise AssertionError(f"V3.7.16 seed {seed}, {workflow}: output mismatch")
        results[str(seed)] = {"workflows": {k: v["digest_sha256"] for k, v in actual["workflows"].items()},
                              "match": True}
    return {"version": "3.7.16", "synthetic_only": True, "seeds": results}


def replay_target_only() -> dict:
    from benchmark_research_performance_v3717 import run_benchmark
    results = {}
    for seed in (3717, 3718):
        expected = json.loads((CUM / f"docs/v3717/benchmark_seed{seed}.json").read_text(encoding="utf-8"))
        actual = run_benchmark(repeats=1, seed=seed)
        if actual["history_sha256"] != expected["history_sha256"]:
            raise AssertionError(f"V3.7.17 seed {seed}: input history differs")
        for workflow, old in expected["workflows"].items():
            now = actual["workflows"][workflow]
            for field in ("legacy_digest", "fast_digest", "exact_same_result"):
                if now[field] != old[field]:
                    raise AssertionError(f"V3.7.17 seed {seed}, {workflow}: {field} mismatch")
        results[str(seed)] = {"workflows": list(actual["workflows"]), "match": True}
    return {"version": "3.7.17", "synthetic_only": True, "seeds": results}


def replay_gacs() -> dict:
    from benchmark_ga_cs_v3715 import run_experiment
    expected = json.loads((CUM / "docs/v3715/benchmark_verified.json").read_text(encoding="utf-8"))
    actual = run_experiment(seeds=(0, 1), evaluations=300, include_infeasible=True)
    if actual["inventory_sha256"] != expected["inventory_sha256"]:
        raise AssertionError("V3.7.15: frozen rule-mask inventory SHA256 differs")
    fields = ("best_genome", "survivors", "fitness", "feasible", "selected_rule_names",
              "candidate_sha256", "evaluations", "independent_oracle_mismatch")
    comparisons = 0
    for scenario, old in expected["scenarios"].items():
        ours = actual["scenarios"][scenario]
        if ours["independent_oracle_mismatches"] != 0:
            raise AssertionError(f"V3.7.15 {scenario}: oracle mismatch")
        lookup = {(trial["seed"], trial["method"]): trial for trial in old["trials"]}
        for trial in ours["trials"]:
            ref = lookup[(trial["seed"], trial["method"])]
            for field in fields:
                if trial[field] != ref[field]:
                    raise AssertionError(f"V3.7.15 {scenario}/{trial['seed']}/{trial['method']}: {field}")
            comparisons += 1
    return {"version": "3.7.15", "synthetic_only": True,
            "seeds": [0, 1], "evaluations_per_method": 300,
            "compared_trials": comparisons, "match": True}


def replay_signed() -> dict:
    from benchmark_signed_blind_v3728 import run
    expected = json.loads((CUM / "runs/v3728/internal_role_rehearsal/summary.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="pl5-cleanroom-") as temp:
        folder = Path(temp)
        actual = run(folder / "public_report", folder / "private_keys", BACKEND)
        # Actual cryptographic keys and signatures are intentionally not copied to CI artifacts.
    comparable = ("schema", "families", "seed", "total_mathematical_tasks",
                  "total_method_rows", "raw_records_digest_sha256", "methods")
    mismatches = [k for k in comparable if actual[k] != expected[k]]
    if mismatches:
        raise AssertionError("V3.7.28 internal rehearsal disagrees with historical baseline: "
                             + ", ".join(mismatches))
    if actual["external_blind_verified"] or actual["lottery_predictive_advantage"] != "NOT_ESTABLISHED":
        raise AssertionError("V3.7.28 evidence classification is incorrect")
    return {"version": "3.7.28", "role_handoff": "internal_only", "external_blind": False,
            "developer_authored": True, "methods": actual["methods"],
            "raw_records_digest_sha256": actual["raw_records_digest_sha256"], "match": True}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("core", "signed"), required=True)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    git_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                             capture_output=True, text=True).stdout.strip()
    result = {"schema": "pl5-cleanroom-replay-v1", "mode": args.mode, "git_sha": git_sha,
              "python": sys.version, "platform": platform.platform(),
              "executable": sys.executable, "results": {}, "failures": [],
              "scientific_scope": "bundled synthetic/internal historical experiments only"}
    steps = ([("inventory", inventory), ("ga_cs_v3715", replay_gacs),
              ("bitmap_v3716", replay_bitmap), ("target_only_v3717", replay_target_only)]
             if args.mode == "core" else [("signed_v3728", replay_signed)])
    for name, action in steps:
        print(f"REPLAY_START {name}", flush=True)
        try:
            result["results"][name] = action()
            print(f"REPLAY_PASS {name}", flush=True)
        except Exception as exc:
            result["failures"].append({"step": name, "type": type(exc).__name__,
                                       "message": str(exc), "traceback": traceback.format_exc()})
            print(f"REPLAY_FAIL {name}: {exc}", file=sys.stderr, flush=True)
    result["status"] = "PASS" if not result["failures"] else "FAIL"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "mode": args.mode,
                      "passed": list(result["results"]),
                      "failed": [x["step"] for x in result["failures"]]}, ensure_ascii=False), flush=True)
    return 0 if not result["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
