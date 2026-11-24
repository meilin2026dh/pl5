"""V3.7.54: exact five-point DFT spectral filter and static independence.

INTERNAL/AI_AUTHORED domain only. No historical data, no new production rule.
"""
from collections import Counter, defaultdict
import cmath
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pl5-cumulative" / "research_backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from number_theory_independence_v3751 import (
    DOMAIN, PRIMES, existing_static_masks, signatures_and_groups,
    _partition, _load_factors,
)

# For digits d[0..4], cyclic C_l = sum_j d_j d_(j+l mod 5).
# |DFT(1)|^2 = (2*C0-C1-C2 + sqrt(5)*(C1-C2))/2
# |DFT(2)|^2 = (2*C0-C1-C2 - sqrt(5)*(C1-C2))/2.
# Hence the predeclared spectral KEEP rule |DFT(1)|^2 > |DFT(2)|^2
# is exactly C1 > C2, using integer arithmetic without float cutoffs.
STATIC_MASK_MANIFEST_SHA256 = "625ab5ee6e7dd932f3e64b0d0f294763e21aa541ae5bcf69b2c7f987d65f7499"


def spectral_invariants(n):
    if type(n) is not int or not 0 <= n < DOMAIN:
        raise ValueError("five-digit ID out of range")
    d = [(n // q) % 10 for q in (10000, 1000, 100, 10, 1)]
    c0 = sum(t*t for t in d)
    c1 = sum(d[j] * d[(j+1) % 5] for j in range(5))
    c2 = sum(d[j] * d[(j+2) % 5] for j in range(5))
    return 2*c0 - c1 - c2, c1 - c2


def dft_energy(n, k):
    d = [(n // q) % 10 for q in (10000, 1000, 100, 10, 1)]
    z = sum(d[j] * cmath.exp(-2j * cmath.pi * k * j / 5)
            for j in range(5))
    return z.real*z.real + z.imag*z.imag


def bitmap_digest(mask):
    return sha256(mask.to_bytes(DOMAIN // 8, "little")).hexdigest()


def add_number_theory_signatures(old_groups):
    # Exactly the nine fixed binary rules used in V3.7.51/V3.7.52.
    factor_mod = _load_factors()
    spf = factor_mod.smallest_prime_factors(DOMAIN)
    fact = [factor_mod.signature_spf(n, spf) for n in range(DOMAIN)]
    new_groups = defaultdict(list)
    for old_key, ids in old_groups.items():
        for n in ids:
            f = fact[n]
            flags = tuple(int(n % p == 0) for p in PRIMES) + (
                int(f[0] >= 3), int(f[1] >= 3), int(f[2] == 1))
            new_groups[(old_key, flags)].append(n)
    return new_groups


def witness_check(groups, witness):
    if witness is None:
        return
    a, b = witness
    if not 0 <= a < DOMAIN or not 0 <= b < DOMAIN or a == b:
        raise AssertionError("invalid witness")
    if not any(a in v and b in v for v in groups.values()):
        raise AssertionError("witness does not share frozen old signatures")
    if (spectral_invariants(a)[1] > 0) == (spectral_invariants(b)[1] > 0):
        raise AssertionError("spectral witness membership does not differ")


def audit():
    static_masks = existing_static_masks()
    manifest = [{"name": name, "sha256": bitmap_digest(mask)}
                for name, mask in static_masks]
    manifest_hash = sha256(json.dumps(
        manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if manifest_hash != STATIC_MASK_MANIFEST_SHA256:
        raise AssertionError("58-rule source manifest differs from frozen V3.7.51")
    base_groups = signatures_and_groups(static_masks)
    augmented_groups = add_number_theory_signatures(base_groups)

    spectral = [spectral_invariants(n) for n in range(DOMAIN)]
    # Feature is the exact algebraic pair (A, B), no floating rounding.
    binary = [int(B > 0) for _, B in spectral]
    n_keep = sum(binary)
    packed = bytearray(DOMAIN // 8)
    for n, keep in enumerate(binary):
        if keep:
            packed[n >> 3] |= 1 << (n & 7)
    mask = int.from_bytes(packed, "little")
    if n_keep != mask.bit_count():
        raise AssertionError("compiled bitmap mismatch")
    full_static = (1 << DOMAIN) - 1
    for _, keep in static_masks:
        full_static &= keep
    factor_mod = _load_factors()
    recurrence = [factor_mod.recurrence_id(a, b)
                  for a in range(10) for b in range(10)]
    if len(set(recurrence)) != 100:
        raise AssertionError("recurrence fixture drift")

    comparisons = {}
    for label, groups in (("58_static", base_groups),
                          ("58_static_plus_9_number_theory", augmented_groups)):
        full = _partition(groups, spectral)
        predicate = _partition(groups, binary)
        witness_check(groups, predicate["witness_ids"])
        comparisons[label] = {
            "equivalence_classes_before": len(groups),
            "full_spectrum": full,
            "predeclared_binary_rule": predicate,
        }
    return {
        "schema": "pl5-spectral-independent-v3754-1",
        "source": "INTERNAL/AI_AUTHORED",
        "domain": DOMAIN,
        "spectral_definition": "five_point_dft_k1_energy_gt_k2_energy",
        "exact_rule": "C1_gt_C2",
        "static_mask_manifest_sha256": manifest_hash,
        "static_mask_count": len(static_masks),
        "previous_binary_rule_count": 9,
        "standalone_retained": n_keep,
        "standalone_mask_sha256": bitmap_digest(mask),
        "recurrence_baseline_count": len(recurrence),
        "recurrence_intersection_retained": sum(binary[n] for n in recurrence),
        "all_58_intersection_count": full_static.bit_count(),
        "all_58_plus_spectral_retained": (full_static & mask).bit_count(),
        "comparisons": comparisons,
        "historical_coverage_measured": False,
        "runtime_cost_measured": False,
        "practical_filter_value_proven": False,
        "full_dynamic_inventory_compared": False,
    }


class SpectralAuditTests(unittest.TestCase):
    def test_algebraic_dft_reference(self):
        # Independent numerical DFT oracle on a predeclared deterministic grid.
        examples = (0, 1, 11111, 12345, 54321, 99999, 10000,
                    10101, 382, 253, 99747)
        examples += tuple(range(0, DOMAIN, 997))
        for n in examples:
            A, B = spectral_invariants(n)
            e1, e2 = dft_energy(n, 1), dft_energy(n, 2)
            self.assertAlmostEqual(e1, (A + 5**0.5 * B)/2, places=8)
            self.assertAlmostEqual(e2, (A - 5**0.5 * B)/2, places=8)
            if B != 0:
                self.assertEqual(B > 0, e1 > e2)

    def test_exact_independence_and_conservation(self):
        r = audit()
        self.assertEqual(r["static_mask_count"], 58)
        self.assertEqual(r["previous_binary_rule_count"], 9)
        self.assertEqual(r["recurrence_baseline_count"], 100)
        for comp in r["comparisons"].values():
            raw = comp["full_spectrum"]
            binary = comp["predeclared_binary_rule"]
            self.assertGreaterEqual(raw["newly_distinguished_pairs"],
                                    binary["newly_distinguished_pairs"])
            self.assertEqual(binary["boolean_novelty_proven"],
                             binary["witness_ids"] is not None)
        self.assertLessEqual(r["all_58_plus_spectral_retained"],
                             r["all_58_intersection_count"])

    def test_independent_small_group_oracle(self):
        groups = {b"x": [0, 1, 2], b"y": [3, 4]}
        values = [1, 0, 1, 0, 0]
        row = _partition(groups, values)
        self.assertEqual(row["newly_distinguished_pairs"], 2)
        self.assertEqual(row["split_old_classes"], 1)
        self.assertEqual(row["witness_ids"], [0, 1])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SpectralAuditTests)
    outcome = unittest.TextTestRunner().run(suite)
    if not outcome.wasSuccessful():
        raise SystemExit(1)
    print("V3754_SPECTRAL_JSON=" + json.dumps(audit(), sort_keys=True))
