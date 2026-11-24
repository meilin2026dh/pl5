"""Exact joint redundancy of ten frozen predicates (three operator families).

INTERNAL/AI_AUTHORED full domain; no historical observations, no fitted rule.
"""
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
import json
import unittest

from conditional_complementarity_v3752 import (
    NAMES, EXPECTED_SINGLETONS, EXPECTED_MANIFEST, choose2,
    new_signatures, difference_histogram, exact_values, direct_value, shapley,
)
from number_theory_independence_v3751 import (
    DOMAIN, existing_static_masks, signatures_and_groups, _load_factors, PRIMES,
)
from spectral_independence_v3754 import spectral_invariants

RULES = NAMES + ("spectral_c1_gt_c2",)
FAMILIES = ("modular", "prime_factor", "spectral")
FAMILY_MASKS = (63, 448, 512)
WIDTH = len(RULES)


def names(s, catalog):
    return [n for i,n in enumerate(catalog) if s & (1 << i)]


def pair_oracle(groups, sig, width):
    """Directly enumerate each original indistinguishable unordered pair."""
    counts = [0] * (1 << width)
    for g in groups:
        for a,b in combinations(g, 2):
            counts[sig[a] ^ sig[b]] += 1
    return counts


def audit_game(hist, catalog):
    width = len(catalog)
    full = (1 << width) - 1
    vals = exact_values(hist, width)
    # Separate non-transform oracle: sum of all patterns hit by the coalition.
    nonzero = [(p,c) for p,c in enumerate(hist) if p and c]
    for s in range(full + 1):
        if vals[s] != sum(c for p,c in nonzero if p & s):
            raise AssertionError("coalition count mismatch")
    credits = shapley(hist, width)
    if sum(credits) != vals[-1]:
        raise AssertionError("Shapley efficiency mismatch")
    best = []
    for k in range(width + 1):
        eligible = [s for s in range(full+1) if s.bit_count() == k]
        maximum = max(vals[s] for s in eligible)
        best.append({"rule_count": k, "max_pairs": maximum,
                     "all_maximizers": [names(s,catalog) for s in eligible
                                        if vals[s] == maximum]})
    minimum = next(row["rule_count"] for row in best if row["max_pairs"] == vals[-1])
    return {
        "all_subset_values": vals,
        "separated": vals[-1],
        "remaining": hist[0],
        "minimum_equivalent_count": minimum,
        "all_minimum_equivalent_subsets": best[minimum]["all_maximizers"],
        "frontier": best,
        "metrics": [
            {"name": n, "singleton": vals[1<<i], "exclusive": hist[1<<i],
             "leave_one_out_loss": vals[-1]-vals[full^(1<<i)],
             "shapley": str(credits[i])}
            for i,n in enumerate(catalog)
        ],
    }


def family_histogram(hist):
    result = [0] * (1 << len(FAMILIES))
    for p,c in enumerate(hist):
        f = sum(1 << i for i,m in enumerate(FAMILY_MASKS) if p & m)
        result[f] += c
    return result


def report():
    old = existing_static_masks()
    manifest = [{"name": n, "sha256": sha256(m.to_bytes(DOMAIN//8, "little")).hexdigest()}
                for n,m in old]
    digest = sha256(json.dumps(manifest,sort_keys=True,
                               separators=(",",":")).encode()).hexdigest()
    if digest != EXPECTED_MANIFEST:
        raise AssertionError("frozen 58-rule manifest drift")
    classes = signatures_and_groups(old)
    groups = [g for g in classes.values() if len(g) > 1]
    sig = [s | (int(spectral_invariants(n)[1]>0)<<9)
           for n,s in enumerate(new_signatures())]
    hist = difference_histogram(groups,sig,WIDTH)
    if hist != pair_oracle(groups,sig,WIDTH):
        raise AssertionError("direct unordered-pair oracle mismatch")
    if sum(hist) != sum(choose2(len(g)) for g in groups):
        raise AssertionError("pair conservation mismatch")
    rules = audit_game(hist,RULES)
    family = audit_game(family_histogram(hist),FAMILIES)
    vals = rules["all_subset_values"]
    expected = EXPECTED_SINGLETONS + (607023,)
    if tuple(vals[1<<i] for i in range(WIDTH)) != expected:
        raise AssertionError("single-rule regression")
    if vals[511] != 1266810 or vals[1023]-vals[511] != 34159:
        raise AssertionError("previous exact independent-contribution regression")
    # Independent signature regrouping of every family coalition and every
    # singleton / leave-one-out rule, plus all optimal frontier coalitions.
    selected = {0,1023}
    selected.update(1<<i for i in range(WIDTH))
    selected.update(1023^(1<<i) for i in range(WIDTH))
    for s,v in enumerate(family["all_subset_values"]):
        union = sum(m for i,m in enumerate(FAMILY_MASKS) if s & (1<<i))
        selected.add(union)
        if vals[union] != v:
            raise AssertionError("family projection mismatch")
    for row in rules["frontier"]:
        selected.update(sum(1<<RULES.index(n) for n in ns)
                        for ns in row["all_maximizers"])
    for s in sorted(selected):
        if direct_value(groups,sig,s) != vals[s]:
            raise AssertionError("regrouping oracle mismatch")
    if any(r["exclusive"] != r["leave_one_out_loss"] for r in rules["metrics"]):
        raise AssertionError("exclusive contribution mismatch")

    # All singleton-exclusive witnesses verified against original 58 bitmaps
    # and an independent trial-division and digit-string predicate oracle.
    factors = _load_factors()
    def independent(n):
        x,y,z = factors.signature_trial(n)
        d = [int(c) for c in f"{n:05d}"]
        # Direct expansion over unordered digit pairs.
        delta = sum(d[i]*d[j]*(1 if min(j-i,5-j+i)==1 else -1)
                    for i in range(5) for j in range(i+1,5))
        flags = tuple(n%p==0 for p in PRIMES)+(x>=3,y>=3,z==1,delta>0)
        return sum(int(v)<<i for i,v in enumerate(flags))
    witnesses = [None]*WIDTH
    for g in groups:
        reps = {}
        for n in g:
            reps.setdefault(sig[n],n)
        for i in range(WIDTH):
            if not hist[1<<i] or witnesses[i] is not None:
                continue
            for s,a in reps.items():
                b = reps.get(s^(1<<i))
                if b is not None:
                    if not all(((m>>a)&1)==((m>>b)&1) for _,m in old):
                        raise AssertionError("exclusive witness old signature mismatch")
                    if independent(a)^independent(b) != 1<<i:
                        raise AssertionError("independent witness predicate mismatch")
                    witnesses[i] = [a,b]
                    break
    for i,r in enumerate(rules["metrics"]):
        if bool(hist[1<<i]) != (witnesses[i] is not None):
            raise AssertionError("exclusive witness completeness")
        r["witness"] = witnesses[i]
    return {
        "schema": "pl5-joint-operator-redundancy-v3755-1",
        "source": "INTERNAL/AI_AUTHORED",
        "static_manifest": digest,
        "old_indistinguishable_pairs": sum(hist),
        "rule_game": rules,
        "family_game": family,
        "oracle_regrouped_subsets": len(selected),
        "candidate_compression_measured": False,
        "historical_coverage_measured": False,
        "runtime_cost_measured": False,
    }


class TestJoint(unittest.TestCase):
    def test_small_duplicate_and_unique(self):
        groups = [[0,1,2,3],[4,5]]
        sig = [0,3,4,7,0,3]
        hist = difference_histogram(groups,sig,3)
        self.assertEqual(hist,pair_oracle(groups,sig,3))
        r = audit_game(hist,("a","duplicate_a","b"))
        self.assertEqual(r["minimum_equivalent_count"],2)
        self.assertEqual(r["all_minimum_equivalent_subsets"],
                         [["a","b"],["duplicate_a","b"]])
        self.assertEqual(r["metrics"][0]["exclusive"],0)
        self.assertEqual(r["metrics"][1]["exclusive"],0)
        self.assertGreater(r["metrics"][2]["exclusive"],0)
        self.assertEqual(sum(Fraction(x["shapley"]) for x in r["metrics"]),r["separated"])

    def test_family_projection(self):
        hist = [0]*1024
        hist[1]=2
        hist[1|2|64]=3
        hist[64|512]=4
        hist[0]=1
        self.assertEqual(family_histogram(hist),[1,2,0,3,0,0,4,0])

    def test_full_domain(self):
        r = report()
        self.assertEqual(r["old_indistinguishable_pairs"],1342071)
        self.assertEqual(r["rule_game"]["separated"],1300969)
        self.assertEqual(r["family_game"]["remaining"],41102)
        self.assertEqual(r["rule_game"]["metrics"][-1]["exclusive"],34159)
        self.assertEqual(len(r["rule_game"]["all_subset_values"]),1024)
        self.assertEqual(len(r["family_game"]["all_subset_values"]),8)


if __name__ == "__main__":
    if not unittest.TextTestRunner().run(
        unittest.defaultTestLoader.loadTestsFromTestCase(TestJoint)).wasSuccessful():
        raise SystemExit(1)
    print("V3755_JOINT_JSON="+json.dumps(report(),sort_keys=True))
