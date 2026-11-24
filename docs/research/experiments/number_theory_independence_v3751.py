"""V3.7.51: exact independence audit versus all V3.7.40 static masks.

INTERNAL/AI_AUTHORED mathematical candidates only; no historical records.
"""
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "pl5-cumulative" / "research_backend"
sys.path.insert(0, str(BACKEND))
from pailie5.legacy_filter_matrix_v3740 import _indicator_rules, _structure_rules
from pailie5.affine_recurrence_filters_v3739 import recurrence_keep_masks

DOMAIN = 100_000
PRIMES = (2, 3, 5, 7, 11, 13)
SOURCE = "INTERNAL/AI_AUTHORED"


def _load_factors():
    path = Path(__file__).with_name("prime_factor_partition_v3750.py")
    spec = importlib.util.spec_from_file_location("frozen_prime_factor_v3750", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def existing_static_masks():
    # Same registered V3.7.40 adapters, without loading demo target records.
    unused = np.empty(0, dtype=np.int32)
    _, old = _indicator_rules(unused)
    _, structural = _structure_rules(unused)
    masks = old + structural
    names = [name for name, _ in masks]
    if len(masks) != 58 or len(set(names)) != len(names):
        raise AssertionError("expected frozen 58 unique V3.7.40 static rules")
    full = (1 << DOMAIN) - 1
    if any(type(mask) is not int or not 0 <= mask <= full for _, mask in masks):
        raise AssertionError("invalid frozen keep bitmap")
    return masks


def signatures_and_groups(masks):
    # A mask membership signature is the complete observable output of
    # the 58 frozen binary predicates. A split within a signature proves
    # a feature is not computable by any Boolean expression over them.
    rows = np.empty((DOMAIN, len(masks)), dtype=np.uint8)
    for j, (_, mask) in enumerate(masks):
        packed = mask.to_bytes(DOMAIN // 8, "little")
        rows[:, j] = np.unpackbits(np.frombuffer(packed, dtype=np.uint8),
                                   bitorder="little")
    signatures = np.packbits(rows, axis=1, bitorder="little")
    groups = defaultdict(list)
    for n in range(DOMAIN):
        groups[signatures[n].tobytes()].append(n)
    return groups


def _partition(groups, feature):
    initial_pairs = split_pairs = split_classes = 0
    witness = None
    for members in groups.values():
        k = len(members)
        initial_pairs += k * (k - 1) // 2
        counts = Counter(feature[n] for n in members)
        separated = k * (k - 1) // 2 - sum(v * (v - 1) // 2 for v in counts.values())
        split_pairs += separated
        if len(counts) > 1:
            split_classes += 1
            if witness is None:
                first = members[0]
                second = next(n for n in members if feature[n] != feature[first])
                witness = [first, second]
    return {
        "old_indistinguishable_pairs": initial_pairs,
        "newly_distinguished_pairs": split_pairs,
        "split_old_classes": split_classes,
        "boolean_novelty_proven": split_pairs > 0,
        "witness_ids": witness,
    }


def _frozen_marginal(feature, recurrence_ids, accepts):
    accepted = [n for n in recurrence_ids if accepts(feature[n])]
    return {"baseline": len(recurrence_ids), "after": len(accepted),
            "marginal_excluded": len(recurrence_ids) - len(accepted)}


def run():
    masks = existing_static_masks()
    groups = signatures_and_groups(masks)
    factors = _load_factors()
    spf = factors.smallest_prime_factors(DOMAIN)
    factor_rows = [factors.signature_spf(n, spf) for n in range(DOMAIN)]
    recurrence_ids = sorted(factors.recurrence_id(a, b)
                            for a in range(10) for b in range(10))
    if len(set(recurrence_ids)) != 100:
        raise AssertionError("recurrence fixture drift")
    combined = (1 << DOMAIN) - 1
    for _, mask in masks:
        combined &= mask
    results = {}
    for p in PRIMES:
        feature = [n % p for n in range(DOMAIN)]
        row = _partition(groups, feature)
        row["predeclared_category"] = "residue_zero"
        row["recurrence_marginal"] = _frozen_marginal(
            feature, recurrence_ids, lambda v: v == 0)
        results["residue_mod_" + str(p)] = row
    factor_specs = (
        ("factor_omega_distinct_ge3", 0, lambda v: v >= 3),
        ("factor_bigomega_ge3", 1, lambda v: v >= 3),
        ("factor_squarefree_one", 2, lambda v: v == 1),
    )
    for name, col, accepts in factor_specs:
        feature = [s[col] for s in factor_rows]
        row = _partition(groups, feature)
        row["predeclared_category"] = name
        row["recurrence_marginal"] = _frozen_marginal(
            feature, recurrence_ids, accepts)
        results[name] = row

    # Independent check of every reported counterexample using 58 original
    # full-domain integer masks and independent factor trial division.
    for name, row in results.items():
        w = row["witness_ids"]
        if w is None:
            if row["newly_distinguished_pairs"] != 0:
                raise AssertionError("missing witness")
            continue
        a, b = w
        if not all(((mask >> a) & 1) == ((mask >> b) & 1)
                   for _, mask in masks):
            raise AssertionError("old rule witness mismatch")
        if name.startswith("residue_mod_"):
            p = int(name.rsplit("_", 1)[1])
            different = a % p != b % p
        else:
            col = next(i for key, i, _ in factor_specs if key == name)
            different = factors.signature_trial(a)[col] != factors.signature_trial(b)[col]
        if not different:
            raise AssertionError("new feature witness mismatch")
    manifest = [{"name": name,
                 "sha256": sha256(mask.to_bytes(DOMAIN // 8, "little")).hexdigest()}
                for name, mask in masks]
    return {
        "schema": "pl5-number-theory-independence-v3751-1",
        "source": SOURCE,
        "existing_catalog": "V3.7.40_STATIC_BOOLEAN_ADAPTERS_ONLY",
        "static_mask_count": len(masks),
        "static_masks_sha256": sha256(json.dumps(
            manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "old_equivalence_class_count": len(groups),
        "old_singleton_class_count": sum(len(v) == 1 for v in groups.values()),
        "existing_full_intersection_count": combined.bit_count(),
        "methods": results,
        "historical_coverage_measured": False,
        "time_varying_methods_included": False,
        "practical_filter_value_proven": False,
    }


class TestIndependence(unittest.TestCase):
    def test_exact_partition_and_witness_oracle(self):
        result = run()
        self.assertEqual(result["static_mask_count"], 58)
        self.assertEqual(len(result["methods"]), 9)
        for row in result["methods"].values():
            self.assertGreaterEqual(row["old_indistinguishable_pairs"],
                                    row["newly_distinguished_pairs"])
            self.assertEqual(row["boolean_novelty_proven"],
                             row["newly_distinguished_pairs"] > 0)
            self.assertEqual(row["boolean_novelty_proven"], row["witness_ids"] is not None)
            self.assertEqual(row["recurrence_marginal"]["baseline"], 100)
            self.assertEqual(row["recurrence_marginal"]["after"] +
                             row["recurrence_marginal"]["marginal_excluded"], 100)

    def test_small_independent_partition_oracle(self):
        groups = {b"a": [0, 1, 2], b"b": [3, 4]}
        feature = [0, 1, 0, 2, 2]
        report = _partition(groups, feature)
        self.assertEqual(report["old_indistinguishable_pairs"], 4)
        self.assertEqual(report["newly_distinguished_pairs"], 2)
        self.assertEqual(report["split_old_classes"], 1)
        self.assertEqual(report["witness_ids"], [0, 1])

    def test_deterministic_replay(self):
        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main(exit=False)
    print("V3751_INDEPENDENCE_JSON=" + json.dumps(run(), sort_keys=True))
