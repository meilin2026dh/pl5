"""Synthetic-only tests for read-only AI100 public failure diagnosis."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze_ai100_public_failures import summarize, digest, GROUPS, ARMS, MODES, SOURCE_COMMIT

PREFIX = "signed_frozen_graded_evidence/"


def fixture(root: Path, *, corrupt_sha=False, forged_completion=False, d_candidate=False):
    rows = []
    for group, num in GROUPS.items():
        for _ in range(num):
            rows.append({"任务ID": f"PL5T{len(rows)+1:03d}_synthetic", "题组": group + ".模拟"})
    csvpath = root / "review.csv"
    with csvpath.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["任务ID", "题组"])
        w.writeheader()
        w.writerows(rows)
    interrupted = rows[60]["任务ID"]
    statuses = {}
    zipfile = root / "synthetic-public.zip"
    with ZipFile(zipfile, "w", ZIP_DEFLATED) as z:
        z.writestr("public_results/summary.json", json.dumps({
            "source_commit": SOURCE_COMMIT, "question_count": 100,
            "evaluation_type": "AI_AUTHORED_INTERNAL_HOLDOUT_NOT_THIRD_PARTY_BLIND",
            "independent_issuer_verified": False}))
        for row in rows:
            task_id, group = row["任务ID"], row["题组"][0]
            status = "INTERRUPTED_BEFORE_FREEZE" if task_id == interrupted else "FROZEN"
            if forged_completion and task_id == interrupted:
                status = "FROZEN"
            path = PREFIX + task_id + "/freeze_status.json"
            raw = json.dumps({"task_id": task_id, "status": status}).encode()
            statuses[task_id] = hashlib.sha256(raw).hexdigest()
            z.writestr(path, raw)
            if task_id == interrupted:
                continue
            for mode in MODES:
                for arm in ARMS:
                    basis = [] if group in ("D", "E") else [{"kind": "synthetic"}]
                    if d_candidate and group == "D" and mode == MODES[0] and arm == ARMS[0]:
                        basis = [{"kind": "synthetic"}]
                    fit = {"candidate_evaluations": 4 if arm == "v3725_ring" else 26,
                           "exact_fit_tables": basis}
                    fit["integrity_sha256"] = digest(fit)
                    frozen = {"fit_sha256": digest({k:v for k,v in fit.items()
                                                    if k != "integrity_sha256"}),
                              "status": "FROZEN" if basis else "ABSTAIN",
                              "reason": None if basis else "no_candidate"}
                    frozen["integrity_sha256"] = digest(frozen)
                    base = PREFIX + task_id + "/solver/" + mode + "/" + arm + "/"
                    z.writestr(base + "fit.json", json.dumps(fit))
                    z.writestr(base + "freeze.json", json.dumps(frozen))
        receipts = dict(statuses)
        if corrupt_sha:
            receipts[rows[0]["任务ID"]] = "0" * 64
        z.writestr("public_results/all_tasks_freeze_status_manifest.json",
                   json.dumps({"source_git_commit": SOURCE_COMMIT,
                               "task_ids": [r["任务ID"] for r in rows],
                               "freeze_receipt_sha256": receipts,
                               "task_freeze_statuses":
                               {"FROZEN": 99, "INTERRUPTED_BEFORE_FREEZE": 1}}))
    return zipfile, csvpath


class PublicAttributionTests(unittest.TestCase):
    def test_100_tasks_and_D_prevalidation_failure(self):
        with tempfile.TemporaryDirectory() as d:
            result = summarize(*fixture(Path(d)))
        self.assertEqual(result["development_tasks_not_independent"], 100)
        self.assertFalse(result["private_labels_read"])
        self.assertTrue(result["public_evidence_only"])
        for mode in MODES:
            for arm in ARMS:
                x = result["aggregate"]["D"][mode][arm]
                self.assertEqual(x["zero_exact_training_candidates"], 10)
                self.assertEqual(x["abstained_before_validation_no_candidate"], 10)
                self.assertEqual(x["denominator"], 10)
                self.assertEqual(x["interrupted_before_global_freeze"] if
                                 "interrupted_before_global_freeze" in x else 0, 0)
                self.assertEqual(result["aggregate"]["C"][mode][arm]
                                 ["interrupted_before_global_freeze"], 1)

    def test_forged_receipt_sha_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "freeze-status SHA256"):
                summarize(*fixture(Path(d), corrupt_sha=True))

    def test_incomplete_task_cannot_be_upgraded_to_frozen(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "inconsistent"):
                summarize(*fixture(Path(d), forged_completion=True))

    def test_D_train_candidate_changes_fail_frozen_pattern(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(AssertionError, "D pattern differs"):
                summarize(*fixture(Path(d), d_candidate=True))


if __name__ == "__main__":
    unittest.main()
