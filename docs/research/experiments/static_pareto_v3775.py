"""V3.7.75: exact static rule-subset Pareto reference.
INTERNAL/AI_AUTHORED. No historical records, mask fitting or production changes.
"""
from math import fsum, comb
from time import perf_counter_ns
from hashlib import sha256
import json
import unittest

from signed_order_v3763 import freeze, partition, DOMAIN, digest
from static_entropy_v3773 import subset_entropies
from entropy_search_v3774 import search

SCALE = 10**8
WEIGHTS = (1,1,1,1,1,1,4,4,4,5,3,8)


def objectives(h, weights):
    n = len(weights)
    if not 1 <= n <= 12 or len(h) != 1 << n:
        raise ValueError("invalid inventory")
    if any(type(w) is not int or w <= 0 for w in weights):
        raise ValueError("positive integer weights required")
    rows = []
    for s in range(1 << n):
        indexes = [j for j in range(n) if s & (1<<j)]
        redundancy = fsum(h[1<<j] for j in indexes)-h[s]
        assert redundancy >= -1e-10
        # Minimization coordinates: negative information, redundancy, cost.
        # Explicit quantization makes dominance transitive and ties auditable.
        rows.append((s, -round(h[s]*SCALE),
                     round(max(0.0,redundancy)*SCALE),
                     sum(weights[j] for j in indexes)))
    return rows


def dominates(a,b):
    return all(x <= y for x,y in zip(a[1:],b[1:])) and a[1:] != b[1:]


def skyline(rows):
    # Ascending cost, then redundancy, then negative information means a later
    # row cannot strictly dominate an earlier row. Preserve equal-objective ties.
    ordered = sorted(rows,key=lambda r:(r[3],r[2],r[1],r[0]))
    front = []
    rejected = {}
    for row in ordered:
        witness = next((p for p in front if dominates(p,row)),None)
        if witness is None:
            front.append(row)
        else:
            rejected[row[0]] = witness[0]
    return sorted(front), rejected


def reference(rows):
    # Independent pairwise dominance test, not reliant on sorting or skyline.
    return sorted(b for b in rows if not any(
        a[1] <= b[1] and a[2] <= b[2] and a[3] <= b[3] and
        (a[1] < b[1] or a[2] < b[2] or a[3] < b[3]) for a in rows))


def compare(h, weights):
    n = len(weights)
    rows = objectives(h,weights)
    report = []
    for k in range(1,n+1):
        pool = [r for r in rows if r[0].bit_count()==k]
        assert len(pool)==comb(n,k)
        front,rejected = skyline(pool)
        assert front==reference(pool)
        assert len(front)+len(rejected)==len(pool)
        assert all(dominates(rows[w],rows[s]) for s,w in rejected.items())
        front_ids = {r[0] for r in front}
        assert all(w in front_ids for w in rejected.values())
        budget = k*n-k*(k-1)//2
        baselines = {}
        for method in ("static","greedy"):
            candidate = search(n,k,h,method,budget)
            s = candidate["subset"]
            baselines[method] = {"subset":s,"queries":candidate["queries"],
                "objectives":rows[s][1:],"on_frontier":s in front_ids,
                "dominance_witness":rejected.get(s)}
        report.append({"rule_budget":k,"enumerated":len(pool),
             "frontier_size":len(front),"dominated_size":len(rejected),
             "frontier":[list(r) for r in front],"entropy_baselines":baselines,
             "distinct_objective_vectors":len({r[1:] for r in front}),
             "witness_ledger_sha256":sha256(json.dumps(sorted(rejected.items()),
                 separators=(",",":")).encode()).hexdigest()})
    return report


def audit():
    names,raw,_ = freeze()
    _,counts = partition(raw,DOMAIN)
    start = perf_counter_ns()
    h = subset_entropies(counts,len(raw))
    precompute_ns = perf_counter_ns()-start
    start = perf_counter_ns()
    models = {"unit":compare(h,(1,)*len(raw)),
              "heterogeneous_abstract":compare(h,WEIGHTS)}
    compare_ns = perf_counter_ns()-start
    for rows in models.values():
        assert sum(r["enumerated"] for r in rows)==4095
    return {"schema":"pl5-static-pareto-v3775-1","source":"INTERNAL/AI_AUTHORED",
            "domain":DOMAIN,"rule_names":names,"rule_mask_sha256":[digest(m) for m in raw],
            "objective_columns":["subset","negative_information_scaled",
                "redundancy_scaled","abstract_additive_cost"],
            "information_scale":SCALE,
            "weights":{"unit":[1]*len(raw),"heterogeneous_abstract":WEIGHTS},
            "models":models,"precompute_ns":precompute_ns,"compare_ns":compare_ns,
            "limitations":["exact dominance on quantized objectives, not unrounded real values",
                "equal rule count within each frontier; no cross-budget dominance",
                "unit cost constant within each budget; heterogeneous weights are abstract",
                "redundancy is total correlation, dependent on joint entropy",
                "additive cost models full evaluation, not short-circuit or measured time",
                "static partition structure only, no historical coverage or retained-set selection",
                "reference computation is unrestricted; baseline search uses prior query ceiling"]}


class Tests(unittest.TestCase):
    def test_ties_and_tradeoffs(self):
        rows = [(0,-3,1,2),(1,-3,1,2),(2,-4,2,2),
                (3,-2,2,3),(4,-5,0,4),(5,-3,1,1)]
        front,rejected = skyline(rows)
        self.assertEqual([r[0] for r in front],[2,4,5])
        self.assertEqual(front,reference(rows))
        self.assertEqual(set(rejected),{0,1,3})
        front,_ = skyline([(0,-3,1,2),(1,-3,1,2)])
        self.assertEqual(len(front),2)

    def test_independent_and_duplicate(self):
        h = subset_entropies([1]*8,3)
        rows = compare(h,(1,2,3))
        self.assertEqual([r["frontier_size"] for r in rows],[1,1,1])
        self.assertEqual(rows[1]["frontier"][0][0],3)
        h = subset_entropies([1,0,0,1,1,0,0,1],3)
        rows = compare(h,(1,1,1))
        self.assertEqual(rows[1]["frontier_size"],2)
        self.assertFalse(rows[1]["entropy_baselines"]["static"]["on_frontier"])
        self.assertTrue(rows[1]["entropy_baselines"]["greedy"]["on_frontier"])

    def test_full(self):
        r = audit()
        for rows in r["models"].values():
            self.assertEqual(len(rows),12)
            self.assertEqual(rows[-1]["frontier_size"],1)
            self.assertTrue(all(x["frontier_size"]>0 for x in rows))
        self.__class__.result = r


if __name__ == "__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3775_PARETO_JSON="+json.dumps(Tests.result,sort_keys=True))
