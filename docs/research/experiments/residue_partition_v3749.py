"""Exact finite-domain modular residue audit. INTERNAL/AI_AUTHORED only."""
from collections import Counter
from hashlib import sha256
import json
import unittest

DOMAIN = 100_000
PRIMES = (2, 3, 5, 7, 11, 13)


def recurrence_id(a, b):
    digits = [a, b]
    for _ in range(3):
        digits.append((digits[-2] + digits[-1]) % 10)
    return sum(d * 10 ** (4 - i) for i, d in enumerate(digits))


def audit():
    ids = tuple(sorted(recurrence_id(a, b) for a in range(10)
                       for b in range(10)))
    assert len(set(ids)) == 100
    packed = bytearray(DOMAIN // 8)
    for n in ids:
        packed[n >> 3] |= 1 << (n & 7)
    cells = []
    for p in PRIMES:
        population = [DOMAIN // p + (r < DOMAIN % p) for r in range(p)]
        observed = Counter(n % p for n in ids)
        retained = [observed[r] for r in range(p)]
        assert sum(population) == DOMAIN and sum(retained) == 100
        cells.append({
            "prime": p, "universe_counts": population,
            "recurrence_counts": retained, "empty_classes": retained.count(0),
            "zero_class_retained": retained[0],
            "zero_class_marginal_excluded": 100 - retained[0],
        })
    return {
        "schema": "pl5-residue-partition-v3749-1",
        "source": "INTERNAL/AI_AUTHORED",
        "domain": DOMAIN, "recurrence_retained": len(ids),
        "recurrence_bitmap_sha256": sha256(packed).hexdigest(),
        "partitions": cells,
        "historical_coverage_measured": False,
        "candidate_rule_validated": False,
    }


class TestResiduePartition(unittest.TestCase):
    def test_universe_exact(self):
        for cell in audit()["partitions"]:
            p = cell["prime"]
            oracle = [0] * p
            for n in range(DOMAIN):
                oracle[n % p] += 1
            self.assertEqual(oracle, cell["universe_counts"])

    def test_independent_digit_oracle(self):
        # Independent closed-form expansion of the three recurrence steps.
        ids = [
            10000*a + 1000*b + 100*((a+b) % 10)
            + 10*((a+2*b) % 10) + ((2*a+3*b) % 10)
            for a in range(10) for b in range(10)
        ]
        self.assertEqual(len(set(ids)), 100)
        for cell in audit()["partitions"]:
            p = cell["prime"]
            self.assertEqual(
                [sum(n % p == r for n in ids) for r in range(p)],
                cell["recurrence_counts"])

    def test_conservation_and_replay(self):
        self.assertEqual(audit(), audit())
        for cell in audit()["partitions"]:
            self.assertEqual(sum(cell["universe_counts"]), DOMAIN)
            self.assertEqual(sum(cell["recurrence_counts"]), 100)
            self.assertEqual(
                cell["zero_class_retained"] + cell["zero_class_marginal_excluded"],
                100)


if __name__ == "__main__":
    unittest.main(exit=False)
    print("V3749_AUDIT_JSON=" + json.dumps(audit(), sort_keys=True))
