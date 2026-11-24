"""V3.7.57 — audit common support of <=100 nonempty frozen intersections.

Retrospective evidence only, INTERNAL/AI_AUTHORED operator rules.
No fitting, selection, new filtering rule, or historical file modifications.
"""
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from historical_operator_walkforward_v3756 import (
    DOMAIN, TEST_WINDOWS, WARMUP, masks, all_coalitions, verified_rows,
)

CAP = 100
TOTAL_SUBSETS = 1024


def pack_mask(m):
    return sha256(m.to_bytes(DOMAIN // 8, "little")).hexdigest()


def audit():
    # All 1024 frozen intersections are computed before reading any
    # historical target; only after all candidate IDs and hashes are frozen
    # do we inspect the 20 crosschecked retrospective targets.
    rules = masks()
    coalitions = all_coalitions(rules)
    if len(coalitions) != TOTAL_SUBSETS:
        raise AssertionError("unexpected coalition catalog")
    feasible = [(s, m) for s, m in enumerate(coalitions)
                if 1 <= m.bit_count() <= CAP]
    empties = sum(m == 0 for m in coalitions)
    union = 0
    sizes = Counter()
    unique = set()
    for _, mask in feasible:
        union |= mask
        sizes[mask.bit_count()] += 1
        unique.add(mask)
    # Independent alternate union oracle: each candidate is admissible
    # iff it belongs to at least one qualifying frozen conjunction.
    witness_oracle = set()
    for n in range(DOMAIN):
        if any((mask >> n) & 1 for _, mask in feasible):
            witness_oracle.add(n)
    union_ids = {n for n in range(DOMAIN) if (union >> n) & 1}
    if union_ids != witness_oracle:
        raise AssertionError("independent union oracle disagrees")
    # Baselines and evaluation rows are only examined after fixed masks
    # and admissible union identities have been frozen.
    rows = verified_rows()
    targets = [int(x[1]) for x in rows[WARMUP:]]
    if len(targets) != TEST_WINDOWS:
        raise AssertionError("window drift")
    hits = [int(target in union_ids) for target in targets]
    membership_count = [
        sum((mask >> target) & 1 for _, mask in feasible)
        for target in targets
    ]
    if hits != [int(n > 0) for n in membership_count]:
        raise AssertionError("per-window union conservation")
    union_k = len(union_ids)
    null_zero_probability = ((DOMAIN - union_k) / DOMAIN) ** TEST_WINDOWS
    # This is descriptive under a hypothetical iid-uniform reference only:
    # it is NOT a valid model-selection p-value.
    return {
        "schema": "pl5-k100-union-v3757-1",
        "source": "RETROSPECTIVE_CROSSCHECKED_TRANSCRIPTS_NOT_SOURCE_AUTHENTICATED",
        "rule_source": "INTERNAL/AI_AUTHORED_FROZEN_TEN_BINARY_RULES",
        "domain": DOMAIN, "cap": CAP,
        "total_coalitions": TOTAL_SUBSETS,
        "eligible_nonempty_coalitions": len(feasible),
        "empty_coalitions": empties,
        "distinct_eligible_candidate_masks": len(unique),
        "eligible_k_histogram": dict(sorted(sizes.items())),
        "union_candidate_count": union_k,
        "union_candidate_mask_sha256": pack_mask(union),
        "union_coverage_20": sum(hits),
        "union_removed_20": TEST_WINDOWS - sum(hits),
        "per_window_union_membership": hits,
        "per_window_feasible_coalition_membership_count": membership_count,
        "hypothetical_iid_uniform_expected_union_coverage": TEST_WINDOWS * union_k / DOMAIN,
        "hypothetical_iid_uniform_zero_coverage_probability": null_zero_probability,
        "hypothetical_reference_not_a_validation_p_value": True,
        "selection_after_outcomes_prohibited": True,
        "historical_data_rewritten": False,
        "historical_source_independently_authenticated": False,
    }


class TestUnion(unittest.TestCase):
    def test_exact_union_oracle(self):
        r = audit()
        self.assertEqual(r["total_coalitions"], TOTAL_SUBSETS)
        self.assertEqual(r["eligible_nonempty_coalitions"], 308)
        self.assertEqual(r["empty_coalitions"], 68)
        self.assertEqual(r["union_coverage_20"], 0)
        self.assertEqual(r["union_removed_20"], 20)
        self.assertEqual(sum(r["eligible_k_histogram"].values()), 308)
        self.assertGreaterEqual(r["union_candidate_count"], 1)
        self.assertLessEqual(r["union_candidate_count"], DOMAIN)

    def test_known_mathematical_null(self):
        r = audit()
        k = r["union_candidate_count"]
        self.assertAlmostEqual(r["hypothetical_iid_uniform_zero_coverage_probability"],
                               (1-k/DOMAIN)**TEST_WINDOWS)
        self.assertEqual(sum(r["per_window_feasible_coalition_membership_count"]), 0)

    def test_frozen_replay(self):
        a, b = audit(), audit()
        self.assertEqual(a, b)


if __name__ == "__main__":
    result=unittest.TextTestRunner().run(
        unittest.defaultTestLoader.loadTestsFromTestCase(TestUnion))
    if not result.wasSuccessful():
        raise SystemExit(1)
    print("V3757_UNION_JSON=" + json.dumps(audit(), sort_keys=True))
