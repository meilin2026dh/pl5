"""V3.7.52: exact conditional complementarity of the nine V3.7.51 filters."""
from collections import Counter
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
import json
import unittest

from number_theory_independence_v3751 import (
    DOMAIN, PRIMES, _load_factors, existing_static_masks, signatures_and_groups,
)

NAMES = tuple("mod_" + str(p) + "_eq0" for p in PRIMES) + (
    "omega_ge3", "bigomega_ge3", "squarefree_eq1",
)
EXPECTED_SINGLETONS = (668209, 593271, 303601, 342861, 269437, 190771,
                       647501, 557473, 652414)
EXPECTED_MANIFEST = "625ab5ee6e7dd932f3e64b0d0f294763e21aa541ae5bcf69b2c7f987d65f7499"


def choose2(n):
    return n * (n - 1) // 2


def new_signatures():
    factors = _load_factors()
    spf = factors.smallest_prime_factors(DOMAIN)
    signatures = []
    for n in range(DOMAIN):
        a, b, c = factors.signature_spf(n, spf)
        flags = tuple(n % p == 0 for p in PRIMES) + (a >= 3, b >= 3, c == 1)
        signatures.append(sum(int(flag) << i for i, flag in enumerate(flags)))
    return signatures


def difference_histogram(groups, signatures, width):
    """Counts of unordered old-indistinguishable pairs by new XOR signature."""
    size = 1 << width
    hist = [0] * size
    for members in groups:
        if len(members) < 2:
            continue
        counts = Counter(signatures[n] for n in members)
        hist[0] += sum(choose2(c) for c in counts.values())
        for (a, ca), (b, cb) in combinations(counts.items(), 2):
            hist[a ^ b] += ca * cb
    return hist


def exact_values(hist, width):
    """Coverage value of every subset via the subset zeta transform."""
    size = 1 << width
    if len(hist) != size or any(type(n) is not int or n < 0 for n in hist):
        raise ValueError("invalid difference histogram")
    zeta = hist.copy()
    for i in range(width):
        bit = 1 << i
        for s in range(size):
            if s & bit:
                zeta[s] += zeta[s ^ bit]
    total = sum(hist)
    return [total - zeta[(size - 1) ^ s] for s in range(size)]


def direct_value(groups, signatures, subset):
    """Independent regrouping oracle (no XOR histogram or transform)."""
    return sum(choose2(len(g)) - sum(choose2(c) for c in
               Counter(signatures[n] & subset for n in g).values())
               for g in groups if len(g) > 1)


def shapley(hist, width):
    credits = [Fraction(0) for _ in range(width)]
    for pattern, count in enumerate(hist):
        if pattern and count:
            share = Fraction(count, pattern.bit_count())
            for i in range(width):
                if pattern & (1 << i):
                    credits[i] += share
    return credits


def named(subset):
    return [name for i, name in enumerate(NAMES) if subset & (1 << i)]


def report():
    masks = existing_static_masks()
    manifest = [{"name": name, "sha256": sha256(mask.to_bytes(
        DOMAIN // 8, "little")).hexdigest()} for name, mask in masks]
    digest = sha256(json.dumps(manifest, sort_keys=True,
                               separators=(",", ":")).encode()).hexdigest()
    if digest != EXPECTED_MANIFEST:
        raise AssertionError("frozen V3.7.51 static mask manifest changed")
    old = list(signatures_and_groups(masks).values())
    groups = [g for g in old if len(g) > 1]
    sig = new_signatures()
    width = len(NAMES)
    full = (1 << width) - 1
    hist = difference_histogram(groups, sig, width)
    values = exact_values(hist, width)
    credits = shapley(hist, width)
    if sum(hist) != sum(choose2(len(g)) for g in groups):
        raise AssertionError("pair conservation failed")
    if tuple(values[1 << i] for i in range(width)) != EXPECTED_SINGLETONS:
        raise AssertionError("V3.7.51 singleton regression")
    if sum(credits) != values[full]:
        raise AssertionError("Shapley efficiency failed")

    # Independent oracle checks ALL 512 portfolios, not just optima.
    for subset, val in enumerate(values):
        if direct_value(groups, sig, subset) != val:
            raise AssertionError(f"portfolio oracle disagreement: {subset}")
    best = []
    for k in range(width + 1):
        candidates = [s for s in range(full + 1) if s.bit_count() == k]
        maximum = max(values[s] for s in candidates)
        winners = [s for s in candidates if values[s] == maximum]
        best.append({"rule_count": k, "max_distinguished_pairs": maximum,
                     "all_maximizing_subsets": [named(s) for s in winners]})
    equivalent = [s for s in range(full + 1) if values[s] == values[full]]
    minimum = min(s.bit_count() for s in equivalent)

    # Each exclusive pair is indistinguishable by all eight other additions.
    witnesses = [None] * width
    for g in groups:
        representative = {}
        for n in g:
            representative.setdefault(sig[n], n)
        for i in range(width):
            if witnesses[i] is not None or not hist[1 << i]:
                continue
            for a, n in representative.items():
                b = a ^ (1 << i)
                if b in representative:
                    witnesses[i] = [n, representative[b]]
                    break
    rows = []
    factors = _load_factors()
    for i, name in enumerate(NAMES):
        witness = witnesses[i]
        if (witness is not None) != bool(hist[1 << i]):
            raise AssertionError("exclusive witness missing")
        if witness:
            a, b = witness
            if not all(((mask >> a) & 1) == ((mask >> b) & 1) for _, mask in masks):
                raise AssertionError("old mask mismatch")
            def oracle(n):
                x, y, z = factors.signature_trial(n)
                return sum(int(flag) << j for j, flag in enumerate(
                    tuple(n % p == 0 for p in PRIMES) + (x >= 3, y >= 3, z == 1)))
            if oracle(a) ^ oracle(b) != 1 << i:
                raise AssertionError("exclusive witness mismatch")
        rows.append({"name": name, "singleton_pairs": values[1 << i],
                     "exclusive_pairs": hist[1 << i],
                     "leave_one_out_loss": values[full] - values[full ^ (1 << i)],
                     "exclusive_witness": witness,
                     "shapley_numerator": credits[i].numerator,
                     "shapley_denominator": credits[i].denominator})
    return {
        "schema": "pl5-conditional-complementarity-v3752-1",
        "source": "INTERNAL/AI_AUTHORED",
        "static_masks_sha256": digest,
        "old_equivalence_classes": len(old),
        "old_indistinguishable_pairs": sum(hist),
        "joint_distinguished_pairs": values[full],
        "joint_remaining_indistinguishable_pairs": hist[0],
        "joint_equivalence_classes": len(old) - len(groups) +
            sum(len({sig[n] for n in g}) for g in groups),
        "minimum_equivalent_rule_count": minimum,
        "all_minimum_equivalent_subsets": [named(s) for s in equivalent
                                           if s.bit_count() == minimum],
        "rule_metrics": rows,
        "frontier": best,
        "all_subset_values": values,
        "difference_histogram": hist,
        "historical_coverage_measured": False,
        "candidate_compression_measured": False,
        "runtime_cost_measured": False,
    }


class TestComplementarity(unittest.TestCase):
    def test_small_pair_oracle(self):
        groups = [[0, 1, 2, 3], [4, 5]]
        sig = [0, 1, 3, 3, 0, 2]
        hist = difference_histogram(groups, sig, 2)
        brute = [0] * 4
        for g in groups:
            for a, b in combinations(g, 2):
                brute[sig[a] ^ sig[b]] += 1
        self.assertEqual(hist, brute)
        vals = exact_values(hist, 2)
        self.assertEqual(vals, [direct_value(groups, sig, s) for s in range(4)])
        self.assertEqual(sum(shapley(hist, 2)), vals[-1])

    def test_duplicate_rule_and_zero_rule(self):
        groups = [[0, 1, 2]]
        hist = difference_histogram(groups, [0, 3, 3], 3)
        self.assertEqual(exact_values(hist, 3), [0, 2, 2, 2, 0, 2, 2, 2])
        self.assertEqual(shapley(hist, 3), [Fraction(1), Fraction(1), Fraction(0)])

    def test_full_domain(self):
        result = report()
        self.assertEqual(len(result["all_subset_values"]), 512)
        self.assertEqual(result["old_indistinguishable_pairs"],
                         result["joint_distinguished_pairs"] +
                         result["joint_remaining_indistinguishable_pairs"])
        for r in result["rule_metrics"]:
            self.assertEqual(r["exclusive_pairs"], r["leave_one_out_loss"])
        self.assertGreaterEqual(result["joint_equivalence_classes"],
                                result["old_equivalence_classes"])
        self.assertLessEqual(result["joint_equivalence_classes"], DOMAIN)


if __name__ == "__main__":
    result = unittest.TextTestRunner().run(
        unittest.defaultTestLoader.loadTestsFromTestCase(TestComplementarity))
    if not result.wasSuccessful():
        raise SystemExit(1)
    print("V3752_COMPLEMENTARITY_JSON=" + json.dumps(report(), sort_keys=True))
