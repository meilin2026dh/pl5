"""V3.7.53: exact nonempty conjunction/contradiction audit for nine fixed rules.

Structural candidate sets only; no historical data or new thresholds.
"""
from collections import Counter
from hashlib import sha256
import json
import unittest

import numpy as np

from number_theory_independence_v3751 import (
    DOMAIN, existing_static_masks, _load_factors,
)
from conditional_complementarity_v3752 import (
    NAMES, EXPECTED_MANIFEST, new_signatures,
)


def pack(flags):
    return int.from_bytes(np.packbits(flags, bitorder="little").tobytes(), "little")


def digest(mask, domain):
    return sha256(mask.to_bytes((domain + 7) // 8, "little")).hexdigest()


def names(s, width):
    return [NAMES[i] for i in range(width) if s & (1 << i)]


def exact_lattice(signatures, baseline, width):
    sig = np.asarray(signatures, dtype=np.int64)
    domain = len(sig)
    size = 1 << width
    if not 1 <= width <= len(NAMES) or not domain:
        raise ValueError("invalid lattice dimensions")
    if np.any(sig < 0) or np.any(sig >= size):
        raise ValueError("invalid rule signature")
    if type(baseline) is not int or not 0 <= baseline < 1 << domain:
        raise ValueError("invalid baseline")
    mask_flags = np.unpackbits(np.frombuffer(
        baseline.to_bytes((domain+7)//8, "little"), dtype=np.uint8),
        bitorder="little")[:domain].astype(bool)
    rules = [pack((sig & (1 << i)) != 0) for i in range(width)]
    bitmaps = [baseline] * size
    for s in range(1, size):
        bit = s & -s
        bitmaps[s] = bitmaps[s ^ bit] & rules[bit.bit_length() - 1]
    counts = [m.bit_count() for m in bitmaps]

    # Independently compute all counts using a superset zeta transform.
    oracle = np.bincount(sig[mask_flags], minlength=size).tolist()
    for i in range(width):
        bit = 1 << i
        for s in range(size):
            if not s & bit:
                oracle[s] += oracle[s | bit]
    if oracle != counts:
        raise AssertionError("superset histogram disagrees with bitmap lattice")
    # Third, direct vector membership checks all exact bitmap identities.
    for s, bitmap in enumerate(bitmaps):
        direct = pack(mask_flags & ((sig & s) == s))
        if direct != bitmap:
            raise AssertionError("direct membership bitmap mismatch")
    return bitmaps, counts


def analyze(signatures, baseline, width, cap=100):
    if type(cap) is not int or cap < 1:
        raise ValueError("cap must be positive")
    bitmaps, counts = exact_lattice(signatures, baseline, width)
    full = (1 << width) - 1
    if not counts[0]:
        raise ValueError("baseline must be nonempty")
    minimal_empty = [s for s in range(1, full + 1) if not counts[s]
                     and all(counts[s ^ (1 << i)] > 0
                             for i in range(width) if s & (1 << i))]
    maximal_nonempty = [s for s in range(full + 1) if counts[s]
                        and all(counts[s | (1 << i)] == 0
                                for i in range(width) if not s & (1 << i))]
    # Completeness: every empty subset contains a minimal contradiction;
    # every nonempty subset is contained in a maximal feasible subset.
    for s in range(full + 1):
        if counts[s] == 0:
            assert any((s & core) == core for core in minimal_empty)
        else:
            assert any((s & m) == s for m in maximal_nonempty)
    grouped = {}
    for s, m in enumerate(bitmaps):
        grouped.setdefault(m, []).append(s)
    frontier = []
    for k in range(width + 1):
        eligible = [s for s in range(full + 1)
                    if s.bit_count() == k and counts[s] > 0]
        minimum = min((counts[s] for s in eligible), default=None)
        frontier.append({
            "rule_count": k,
            "nonempty_subsets": len(eligible),
            "minimum_positive_retained": minimum,
            "all_minimizers": [s for s in eligible if counts[s] == minimum],
        })
    cap_sets = [s for s in range(full + 1) if 0 < counts[s] <= cap]
    min_rules = min((s.bit_count() for s in cap_sets), default=None)
    # Count exact output equivalence, not merely equal cardinality.
    classes = [{
        "bitmap_sha256": digest(m, len(signatures)),
        "retained": m.bit_count(),
        "subsets": ss,
        "minimum_rule_count": min(s.bit_count() for s in ss),
    } for m, ss in grouped.items()]
    return {
        "baseline_count": counts[0],
        "baseline_sha256": digest(baseline, len(signatures)),
        "all_rules_retained": counts[-1],
        "empty_subsets": sum(n == 0 for n in counts),
        "nonempty_subsets": sum(n > 0 for n in counts),
        "distinct_output_bitmaps": len(grouped),
        "nonempty_distinct_output_bitmaps": sum(m != 0 for m in grouped),
        "minimal_empty_subsets": [{"subset": s, "rules": names(s,width),
                                   "immediate_predecessor_counts":
                                   [counts[s ^ (1 << i)] for i in range(width)
                                    if s & (1 << i)]} for s in minimal_empty],
        "maximal_nonempty_subsets": [{"subset": s, "rules": names(s,width),
                                     "retained": counts[s]} for s in maximal_nonempty],
        "frontier": frontier,
        "cap": cap, "cap_feasible_subsets": len(cap_sets),
        "minimum_added_rules_for_cap": min_rules,
        "all_minimum_rule_cap_subsets": [
            s for s in cap_sets if s.bit_count() == min_rules],
        "counts": counts,
        "equivalent_output_classes": classes,
    }


def report():
    old_masks = existing_static_masks()
    manifest = [{"name": name, "sha256": digest(m, DOMAIN)}
                for name,m in old_masks]
    manifest_hash = sha256(json.dumps(manifest, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    if manifest_hash != EXPECTED_MANIFEST:
        raise AssertionError("old mask manifest changed")
    sig = new_signatures()
    full = (1 << DOMAIN) - 1
    old = full
    for _, mask in old_masks:
        old &= mask
    factors = _load_factors()
    recurrence = 0
    for a in range(10):
        for b in range(10):
            recurrence |= 1 << factors.recurrence_id(a,b)
    assert recurrence.bit_count() == 100 and old.bit_count() == 2
    result = {
        "schema": "pl5-number-theory-conjunction-v3753-1",
        "source": "INTERNAL/AI_AUTHORED",
        "static_masks_sha256": manifest_hash,
        "rules": NAMES,
        "baselines": {
            "full_domain": analyze(sig, full, len(NAMES)),
            "fixed_recurrence": analyze(sig, recurrence, len(NAMES)),
            "full_old_intersection": analyze(sig, old, len(NAMES)),
        },
        "historical_coverage_measured": False,
        "wall_clock_measured": False,
    }
    return result


class TestConjunction(unittest.TestCase):
    def test_duplicate_conflict_and_exact_identity(self):
        # Rule 0 and 1 are duplicates; rule 2 has disjoint keep set.
        sig = [3,3,4,4,0]
        r = analyze(sig, 31, 3, cap=2)
        self.assertEqual(r["counts"], [5,2,2,2,2,0,0,0])
        self.assertEqual([x["subset"] for x in r["minimal_empty_subsets"]], [5,6])
        self.assertEqual([x["subset"] for x in r["maximal_nonempty_subsets"]], [3,4])
        self.assertEqual(r["distinct_output_bitmaps"], 4)
        self.assertEqual(r["all_minimum_rule_cap_subsets"], [1,2,4])

    def test_restrict_baseline_and_unreachable_cap(self):
        sig = [3,3,3,0]
        r = analyze(sig, 7, 2, cap=1)
        self.assertEqual(r["counts"], [3,3,3,3])
        self.assertEqual(r["distinct_output_bitmaps"], 1)
        self.assertIsNone(r["minimum_added_rules_for_cap"])

    def test_full_domain(self):
        r = report()
        baselines = r["baselines"]
        self.assertEqual([baselines[k]["baseline_count"] for k in
            ("full_domain", "fixed_recurrence", "full_old_intersection")],
            [100000,100,2])
        for value in baselines.values():
            self.assertEqual(value["empty_subsets"] + value["nonempty_subsets"],512)
            self.assertEqual(len(value["counts"]),512)
            self.assertEqual(sum(len(c["subsets"]) for c in
                                 value["equivalent_output_classes"]),512)
        # Preserve singleton marginal results already frozen in V3.7.51.
        self.assertEqual([baselines["full_old_intersection"]["counts"][1<<i]
                          for i in range(9)], [1,1,0,1,0,0,1,1,2])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestConjunction)
    if not unittest.TextTestRunner().run(suite).wasSuccessful():
        raise SystemExit(1)
    print("V3753_CONJUNCTION_JSON=" + json.dumps(report(), sort_keys=True))
