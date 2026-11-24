"""V3.7.50 fixed prime-factor partition audit; INTERNAL/AI_AUTHORED."""
from collections import Counter
from hashlib import sha256
import json
import math
import unittest

DOMAIN = 100_000


def smallest_prime_factors(limit):
    spf = list(range(limit))
    for p in range(2, math.isqrt(limit - 1) + 1):
        if spf[p] == p:
            for multiple in range(p * p, limit, p):
                if spf[multiple] == multiple:
                    spf[multiple] = p
    return spf


def signature_spf(n, spf):
    if n < 2:
        return (-1 if n == 0 else 0, -1 if n == 0 else 0, -1 if n == 0 else 1)
    distinct = total = 0
    squarefree = 1
    while n > 1:
        prime = spf[n]
        exponent = 0
        while n % prime == 0:
            n //= prime
            exponent += 1
        distinct += 1
        total += exponent
        if exponent > 1:
            squarefree = 0
    return distinct, total, squarefree


def signature_trial(n):
    if n < 2:
        return (-1, -1, -1) if n == 0 else (0, 0, 1)
    distinct = total = 0
    squarefree = 1
    p = 2
    while p * p <= n:
        exponent = 0
        while n % p == 0:
            n //= p
            exponent += 1
        if exponent:
            distinct += 1
            total += exponent
            squarefree &= int(exponent == 1)
        p += 1
    if n > 1:
        distinct += 1
        total += 1
    return distinct, total, squarefree


def recurrence_id(a, b):
    digits = [a, b]
    for _ in range(3):
        digits.append((digits[-2] + digits[-1]) % 10)
    return sum(d * 10**(4 - i) for i, d in enumerate(digits))


def audit():
    spf = smallest_prime_factors(DOMAIN)
    signatures = [signature_spf(n, spf) for n in range(DOMAIN)]
    ids = sorted(recurrence_id(a, b) for a in range(10) for b in range(10))
    assert len(set(ids)) == 100
    feature_names = ("omega_distinct", "big_omega_total", "squarefree")
    metrics = {}
    for column, name in enumerate(feature_names):
        universe = Counter(s[column] for s in signatures)
        retained = Counter(signatures[n][column] for n in ids)
        classes = sorted(universe)
        last = [set() for _ in range(10)]
        mod7 = [set() for _ in range(7)]
        for n, sig in enumerate(signatures):
            last[n % 10].add(sig[column])
            mod7[n % 7].add(sig[column])
        metrics[name] = {
            "domain_counts": {str(v): universe[v] for v in classes},
            "recurrence_counts": {str(v): retained[v] for v in classes},
            "distinct_values_per_last_digit": [len(x) for x in last],
            "distinct_values_per_mod7": [len(x) for x in mod7],
            "determined_by_last_digit": all(len(x) == 1 for x in last),
            "determined_by_mod7": all(len(x) == 1 for x in mod7),
        }
        assert sum(universe.values()) == DOMAIN
        assert sum(retained.values()) == 100
    encoded = json.dumps(signatures, separators=(",", ":"), ensure_ascii=True).encode()
    return {
        "schema": "pl5-prime-factor-partition-v3750-1",
        "source": "INTERNAL/AI_AUTHORED",
        "domain": DOMAIN,
        "recurrence_count": len(ids),
        "signature_table_sha256": sha256(encoded).hexdigest(),
        "metrics": metrics,
        "historical_coverage_measured": False,
        "complete_rule_inventory_redundancy_measured": False,
        "candidate_rule_validated": False,
    }


class TestPrimeFactorAudit(unittest.TestCase):
    def test_full_domain_independent_factorization(self):
        spf = smallest_prime_factors(DOMAIN)
        for n in range(DOMAIN):
            self.assertEqual(signature_spf(n, spf), signature_trial(n), n)

    def test_independent_recurrence_oracle(self):
        ids = [10000*a + 1000*b + 100*((a+b)%10)
               + 10*((a+2*b)%10) + (2*a+3*b)%10
               for a in range(10) for b in range(10)]
        self.assertEqual(len(set(ids)), 100)
        result = audit()
        for i, name in enumerate(("omega_distinct", "big_omega_total", "squarefree")):
            expected = Counter(signature_trial(n)[i] for n in ids)
            actual = result["metrics"][name]["recurrence_counts"]
            self.assertEqual({str(k): expected[k] for k in map(int, actual)}, actual)

    def test_conservation_and_replay(self):
        a = audit()
        self.assertEqual(a, audit())
        for metric in a["metrics"].values():
            self.assertEqual(sum(metric["domain_counts"].values()), DOMAIN)
            self.assertEqual(sum(metric["recurrence_counts"].values()), 100)
            self.assertFalse(metric["determined_by_last_digit"])
            self.assertFalse(metric["determined_by_mod7"])


if __name__ == "__main__":
    unittest.main(exit=False)
    print("V3750_AUDIT_JSON=" + json.dumps(audit(), sort_keys=True))
