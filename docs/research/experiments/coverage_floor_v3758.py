"""V3.7.58 retrospective coverage-floor certificate for ten frozen filters.

The per-record minimum feasible K is a post-hoc diagnostic, not a selection
strategy. It is proven over all 1024 Boolean AND subsets without changing them.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from historical_operator_walkforward_v3756 import (
    DOMAIN, TEST_WINDOWS, WARMUP, RULE_NAMES, masks, all_coalitions, verified_rows
)

CAPS = (100, 500, 1000, 5000, 10000, 20000, 50000, 100000)
FULL_RULESET = (1 << len(RULE_NAMES)) - 1


def _bitmap_sha(mask):
    return sha256(mask.to_bytes(DOMAIN // 8, "little")).hexdigest()


def frozen_support():
    rule_masks = masks()
    if len(rule_masks) != len(RULE_NAMES):
        raise AssertionError("rule inventory drift")
    coalitions = all_coalitions(rule_masks)
    if len(coalitions) != 1024:
        raise AssertionError("subset inventory drift")

    # Construct the complete capped union of all frozen subsets at every
    # predeclared cap before opening any historical outcome.
    support = {}
    for cap in CAPS:
        union = 0
        eligible = 0
        for m in coalitions:
            k = m.bit_count()
            if 1 <= k <= cap:
                eligible += 1
                union |= m
        support[cap] = (union, eligible)
    return rule_masks, coalitions, support


def exact_target_floor(n, rule_masks, coalitions):
    # S consists precisely of those rules satisfied by the given ID.
    # Every retained coalition must be a subset of S. The conjunction of
    # all of S therefore has the smallest candidate count of any retaining
    # coalition. This is an exact structural theorem, not fitted calibration.
    s = sum(((mask >> n) & 1) << i for i, mask in enumerate(rule_masks))
    kmin = coalitions[s].bit_count()
    if not ((coalitions[s] >> n) & 1):
        raise AssertionError("maximal compatible rule subset excludes ID")
    # Independent exhaustive oracle including ties.
    admissible = [(subset, bm.bit_count()) for subset, bm in enumerate(coalitions)
                  if (bm >> n) & 1]
    brute = min(k for _, k in admissible)
    if brute != kmin:
        raise AssertionError("minimum K proof disagrees with exhaustive oracle")
    return s, kmin, len([1 for _, k in admissible if k == kmin])


def audit():
    rule_masks, coalitions, supports = frozen_support()
    rows = verified_rows()
    targets = rows[WARMUP:]
    if len(targets) != TEST_WINDOWS:
        raise AssertionError("evaluation-window drift")
    certificates = []
    for issue, digits in targets:
        n = int(digits)
        compatible, kmin, ties = exact_target_floor(n, rule_masks, coalitions)
        result = {
            "issue": issue,
            "compatible_rule_bits": compatible,
            "compatible_rules": [name for i, name in enumerate(RULE_NAMES)
                                 if (compatible >> i) & 1],
            "minimum_retained_k_to_include_target": kmin,
            "minimizing_subset_count": ties,
            "caps_allowing_some_frozen_conjunction": [
                cap for cap in CAPS if kmin <= cap
            ],
        }
        for cap, (union, _) in supports.items():
            # A subset of cap retains n iff its frozen union contains n.
            if int((union >> n) & 1) != int(kmin <= cap):
                raise AssertionError("capped union vs minimum-K theorem disagrees")
        certificates.append(result)
    caps = {}
    for cap, (union, eligible) in supports.items():
        caps[str(cap)] = {
            "nonempty_subsets_at_cap": eligible,
            "union_k": union.bit_count(),
            "union_sha256": _bitmap_sha(union),
            "historical_covered": sum(c["minimum_retained_k_to_include_target"] <= cap
                                      for c in certificates),
            "historical_removed": sum(c["minimum_retained_k_to_include_target"] > cap
                                      for c in certificates),
        }
    floors = [row["minimum_retained_k_to_include_target"] for row in certificates]
    return {
        "schema": "pl5-frozen-coverage-floor-v3758-1",
        "candidate_domain": DOMAIN,
        "source": "RETROSPECTIVE_CROSSCHECKED_TRANSCRIPTS_NOT_SOURCE_AUTHENTICATED",
        "operator_rules": "INTERNAL/AI_AUTHORED_TEN_FROZEN_BINARY_PREDICATES",
        "all_boolean_and_subsets": len(coalitions),
        "evaluation_issues": [issue for issue, _ in targets],
        "evaluated_target_count": len(targets),
        "per_target_minimum_k": certificates,
        "minimum_k_min": min(floors),
        "minimum_k_max": max(floors),
        "minimum_k_distribution": dict(sorted(Counter(floors).items())),
        "cap_frontier": caps,
        "historical_coverage_observed": True,
        "post_hoc_target_floor_is_not_selection_policy": True,
        "unseen_future_validity_established": False,
        "historical_source_bytes_modified": False,
    }


class CoverageFloorTests(unittest.TestCase):
    def test_frozen_domain_and_full_cap(self):
        r = audit()
        self.assertEqual(r["all_boolean_and_subsets"], 1024)
        self.assertEqual(r["evaluated_target_count"], 20)
        self.assertEqual(r["cap_frontier"]["100"]["nonempty_subsets_at_cap"], 308)
        self.assertEqual(r["cap_frontier"]["100"]["union_k"], 1215)
        self.assertEqual(r["cap_frontier"]["100"]["historical_covered"], 0)
        self.assertEqual(r["cap_frontier"]["100000"]["historical_covered"], 20)

    def test_small_independent_oracle(self):
        # Three finite-domain masks; identity 2 satisfies rule 0 only.
        example = (0b0111, 0b1011, 0b1010)
        subsets = [0b1111] * 8
        for s in range(1, 8):
            bit = s & -s
            subsets[s] = subsets[s ^ bit] & example[bit.bit_length()-1]
        for n in range(4):
            _, count, _ = exact_target_floor(n, example, subsets)
            self.assertEqual(count, min(x.bit_count() for x in subsets
                                       if (x >> n) & 1))

    def test_deterministic_full_replay(self):
        self.assertEqual(audit(), audit())


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CoverageFloorTests)
    if not unittest.TextTestRunner().run(suite).wasSuccessful():
        raise SystemExit(1)
    r = audit()
    print("V3758_FLOOR_JSON=" + json.dumps(r, sort_keys=True))
