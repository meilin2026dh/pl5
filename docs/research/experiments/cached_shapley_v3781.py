"""V3.7.81: reuse marginal differences in the static Shapley audit.
INTERNAL/AI_AUTHORED. Fixed inventory; no historical records or new rules.
Hypothesis: cardinality denominators and cached subset marginals reduce
audit time while preserving every contribution and conditional MI check.
"""
from itertools import permutations
from math import comb, fsum, isclose, factorial
from random import Random
from statistics import median
from time import perf_counter_ns
import json
import platform
import unittest

from signed_order_v3763 import freeze, partition, DOMAIN, digest
from static_entropy_v3773 import decompose, TOL
from shared_entropy_v3780 import shared_entropies, fingerprint

SOURCE_HEAD = "5f99d4fc646a6ddc048c98c0e7f08a66d8c3bedc"


def submasks(mask):
    """Ascending submasks, including zero and mask."""
    s = 0
    while True:
        yield s
        if s == mask:
            return
        s = (s-mask) & mask


def cached_decompose(h, n):
    if not 1 <= n <= 12 or len(h) != 1 << n:
        raise ValueError("invalid bounded inventory")
    full = (1 << n)-1
    denominators = [n*comb(n-1,k) for k in range(n)]
    values = []
    violations = 0
    largest = smallest = 0.0
    for j in range(n):
        bit = 1 << j
        free = full ^ bit
        delta = [0.0]*(1 << n)
        terms = []
        for s in submasks(free):
            d = h[s|bit]-h[s]
            assert d >= -TOL
            delta[s] = d
            terms.append(d/denominators[s.bit_count()])
        # Each unordered pair and each conditioning subset exactly once.
        # The cached difference uses the same floating operations as reference.
        for i in range(j+1,n):
            b = 1 << i
            for s in submasks(free ^ b):
                cmi = delta[s]-delta[s|b]
                violations += cmi < -TOL
                if cmi > largest:
                    largest = cmi
                if cmi < smallest:
                    smallest = cmi
        values.append({"singleton_bits":h[bit],
                       "leave_one_out_bits":h[full]-h[full^bit],
                       "shapley_bits":fsum(terms)})
    assert violations == 0
    assert isclose(fsum(v["shapley_bits"] for v in values),h[full],abs_tol=TOL)
    return values, {"submodularity_violations":violations,
                    "largest_conditional_mi_bits":largest,
                    "smallest_conditional_mi_bits":smallest}


def permutation_reference(h,n):
    terms = [[] for _ in range(n)]
    for order in permutations(range(n)):
        s = 0
        for j in order:
            t = s | (1 << j)
            terms[j].append(h[t]-h[s])
            s = t
    return [fsum(v)/factorial(n) for v in terms]


def audit():
    names,masks,_ = freeze()
    n = len(masks)
    assert n == 12
    _,counts = partition(masks,DOMAIN)
    h = shared_entropies(counts,n)
    # Pin the previous evidence ledger, not timing values.
    assert fingerprint(h) == "771a4885ca6480866cd3321ba0345c0902f173de57f5a954374ea71ccd5b1242"
    methods = {"reference":decompose,"cached":cached_decompose}
    expected = decompose(h,n)
    assert cached_decompose(h,n) == expected
    trials = []
    for i in range(6):
        order = tuple(methods) if i % 2 == 0 else tuple(reversed(methods))
        row = {"order":order}
        for label in order:
            start = perf_counter_ns()
            result = methods[label](h,n)
            row[label+"_ns"] = perf_counter_ns()-start
            assert result == expected
        trials.append(row)
    values,checks = expected
    return {"schema":"pl5-cached-shapley-v3781-1","source":"INTERNAL/AI_AUTHORED",
            "source_head":SOURCE_HEAD,"domain":DOMAIN,"rule_names":names,
            "rule_mask_sha256":[digest(m) for m in masks],
            "entropy_ledger_sha256":fingerprint(h),
            "decomposition_sha256":fingerprint(expected),
            "subsets":len(h),"exact_within_platform_equality":True,
            "shapley_bits":[v["shapley_bits"] for v in values],"checks":checks,
            "analytical_work":{
                "marginal_terms":n*(1 << (n-1)),
                "conditional_mi_checks":comb(n,2)*(1 << (n-2)),
                "reference_entropy_differences":n*(1 << (n-1))+comb(n,2)*(1 << (n-2)),
                "cached_entropy_differences":n*(1 << (n-1)),
                "reference_denominator_evaluations":n*(1 << (n-1)),
                "cached_denominator_evaluations":n,
                "extra_delta_slots_per_rule":1 << n},
            "paired_trials":trials,
            "median_paired_ratio":median(t["reference_ns"]/max(1,t["cached_ns"]) for t in trials),
            "platform":platform.platform(),"python":platform.python_version(),
            "limitations":["static fixed entropy ledger; no new filtering rules or historical coverage",
                           "only decomposition phase timed; no complete audit speed claim",
                           "six alternating warm pairs; descriptive timing, no timing gate",
                           "analytical work counts are not CPU instruction counts",
                           "extra delta list memory not measured; bounded to 12 rules",
                           "cross-platform fingerprint uses prior quantization"]}


class Tests(unittest.TestCase):
    def test_submasks(self):
        for mask in range(256):
            self.assertEqual(list(submasks(mask)),
                             [s for s in range(mask+1) if s & mask == s])

    def test_decomposition_and_permutations(self):
        rng = Random(3781)
        cases = [(2,[2,0,0,2]),(3,[1,0,0,1,0,1,1,0]),(1,[0,1])]
        for n in range(1,7):
            cases.extend([(n,[1]*(1<<n)),
                          (n,[rng.randrange(1,8) for _ in range(1<<n)]),
                          (n,[9]+[0]*((1<<n)-1))])
        for n,counts in cases:
            h = shared_entropies(counts,n)
            a = cached_decompose(h,n)
            self.assertEqual(a,decompose(h,n))
            for value,ref in zip(a[0],permutation_reference(h,n)):
                self.assertAlmostEqual(value["shapley_bits"],ref,places=10)

    def test_invalid(self):
        for h,n in (([],1),([0],0),([0,1],13)):
            with self.assertRaises(ValueError):
                cached_decompose(h,n)
        for h in ([0,1,1,0],[0,1,1,3]):
            with self.assertRaises(AssertionError):
                cached_decompose(h,2)

    def test_full(self):
        report = audit()
        self.assertEqual(report["subsets"],4096)
        self.assertEqual(report["analytical_work"]["conditional_mi_checks"],67584)
        self.assertEqual(len(report["paired_trials"]),6)
        self.__class__.result = report


if __name__ == "__main__":
    if not unittest.TextTestRunner().run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3781_CACHED_SHAPLEY_JSON="+json.dumps(Tests.result,sort_keys=True,allow_nan=False))
