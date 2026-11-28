"""V3.7.74: bounded static rule-subset entropy search comparison.

INTERNAL/AI_AUTHORED. Objective is joint entropy of a Boolean partition
on a fixed uniform finite domain, not selection of a retained atom.
No historical records or new rule masks.
"""
from itertools import combinations
from math import comb, fsum
from random import Random
from time import perf_counter_ns
import json
import unittest

from signed_order_v3763 import freeze, partition, DOMAIN, digest
from static_entropy_v3773 import subset_entropies, TOL

SEEDS = tuple(range(16))


class Oracle:
    """Charge each distinct subset evaluation; no access to reference ranking."""
    def __init__(self, h, budget):
        self._h = h
        self.budget = budget
        self.cache = {}

    def score(self, s):
        if s not in self.cache:
            if len(self.cache) >= self.budget:
                raise RuntimeError("objective query budget exceeded")
            self.cache[s] = self._h[s]
        return self.cache[s]


def best(items, score):
    # Tie-break by smallest mask, within numerical tolerance of true maximum.
    rows = [(s, score(s)) for s in items]
    v = max(x[1] for x in rows)
    return min(s for s, value in rows if value >= v-TOL)


def search(n, k, h, method, budget, seed=0):
    q = Oracle(h,budget)
    if method == "static":
        singleton = [1 << j for j in range(n)]
        chosen = 0
        for _ in range(k):
            b = best(singleton,q.score)
            singleton.remove(b)
            chosen |= b
    elif method == "greedy":
        chosen = 0
        for _ in range(k):
            chosen = best((chosen | (1<<j) for j in range(n)
                           if not chosen & (1<<j)),q.score)
    elif method == "random":
        pool = [sum(1<<j for j in c) for c in combinations(range(n),k)]
        chosen = best(Random(seed).sample(pool,min(budget,len(pool))),q.score)
    else:
        raise ValueError(method)
    value = q.score(chosen)
    assert chosen.bit_count()==k and len(q.cache)<=budget
    return {"subset":chosen,"entropy_bits":value,"queries":len(q.cache)}


def compare(h,n):
    rows = []
    for k in range(1,n+1):
        # Greedy performs n + (n-1) + ... + (n-k+1) evaluations.
        # All bounded methods receive that same ceiling, not forced padding.
        budget = k*n-k*(k-1)//2
        pool = [s for s in range(1<<n) if s.bit_count()==k]
        assert len(pool)==comb(n,k)
        optimum = max(h[s] for s in pool)
        exact = min(s for s in pool if h[s]>=optimum-TOL)
        def annotate(r):
            regret = max(0.0,optimum-r["entropy_bits"])
            assert r["entropy_bits"]<=optimum+TOL
            return dict(r, regret_bits=regret, optimum_within_tolerance=regret<=TOL)
        static = annotate(search(n,k,h,"static",budget))
        greedy = annotate(search(n,k,h,"greedy",budget))
        random = [dict(seed=seed,**annotate(search(n,k,h,"random",budget,seed)))
                  for seed in SEEDS]
        assert greedy["queries"]==budget
        assert greedy["entropy_bits"]+TOL >= (1-(1-1/k)**k)*optimum
        rows.append({"rule_budget":k,"query_ceiling":budget,
                     "exact_reference":{"subset":exact,"entropy_bits":optimum,
                                        "enumerated_subsets":len(pool)},
                     "static":static,"greedy":greedy,"random_trials":random,
                     "random_mean_regret_bits":fsum(r["regret_bits"] for r in random)/len(random),
                     "random_optimal_trials":sum(r["optimum_within_tolerance"] for r in random)})
    return rows


def audit():
    names,raw,_=freeze()
    _,counts=partition(raw,DOMAIN)
    t=perf_counter_ns()
    h=subset_entropies(counts,len(raw))
    setup_ns=perf_counter_ns()-t
    t=perf_counter_ns()
    rows=compare(h,len(raw))
    compare_ns=perf_counter_ns()-t
    return {"schema":"pl5-entropy-search-v3774-1","source":"INTERNAL/AI_AUTHORED",
            "domain":DOMAIN,"rule_names":names,"rule_mask_sha256":[digest(m) for m in raw],
            "precompute_ns":setup_ns,"comparison_ns":compare_ns,"rows":rows,
            "limitations":["same rule-count budget and objective-query ceiling, not identical consumed queries",
                "exact reference is unrestricted; lookup table precomputed for all methods",
                "query counts do not measure end-to-end execution costs",
                "random draws unique subsets per trial; 16 fixed seeds, descriptive only",
                "static uniform partition entropy, not candidate retention or historical coverage",
                "no new rules, production changes or timing gates"]}


class Tests(unittest.TestCase):
    def test_independent(self):
        rows=compare(subset_entropies([1]*8,3),3)
        for r in rows:
            self.assertAlmostEqual(r["exact_reference"]["entropy_bits"],r["rule_budget"])
            self.assertTrue(r["greedy"]["optimum_within_tolerance"])
            self.assertTrue(r["static"]["optimum_within_tolerance"])

    def test_duplicate_rule_and_budget(self):
        # Coordinates 0 and 1 are duplicates, coordinate 2 independent.
        h=subset_entropies([1,0,0,1,1,0,0,1],3)
        rows=compare(h,3)
        self.assertAlmostEqual(rows[1]["static"]["regret_bits"],1)
        self.assertAlmostEqual(rows[1]["greedy"]["regret_bits"],0)
        self.assertEqual(rows,compare(h,3))
        q=Oracle(h,1)
        self.assertEqual(q.score(1),q.score(1))
        with self.assertRaises(RuntimeError):
            q.score(2)

    def test_full(self):
        r=audit()
        self.assertEqual(len(r["rows"]),12)
        self.assertEqual(sum(x["exact_reference"]["enumerated_subsets"] for x in r["rows"]),4095)
        self.assertAlmostEqual(r["rows"][-1]["exact_reference"]["entropy_bits"],7.750775673605337)
        self.__class__.result=r


if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3774_SEARCH_JSON="+json.dumps(Tests.result,sort_keys=True))
