"""V3.7.76: measured projection-cost sensitivity of static Pareto frontiers.

INTERNAL/AI_AUTHORED. Fixed full-domain partition, all nonempty subsets.
No historical records, no rule fitting or retained-set selection.
"""
from collections import Counter
from hashlib import sha256
from math import fsum, log2
from random import Random
from statistics import median
from time import perf_counter_ns
import json
import platform
import unittest

from signed_order_v3763 import freeze, partition, DOMAIN, digest
from static_entropy_v3773 import subset_entropies, TOL
from static_pareto_v3775 import objectives, skyline, reference, WEIGHTS
from entropy_search_v3774 import search

SEEDS = (760,761,762,763,764)


def project(occupied, subset):
    """Materialize counts of the projected truth signatures."""
    groups = {}
    for s,k in occupied:
        key = s & subset
        groups[key] = groups.get(key,0)+k
    return groups


def entropy(groups, total):
    return fsum(-k/total*log2(k/total) for k in sorted(groups.values()))


def front_ids(rows):
    front, rejected = skyline(rows)
    return {r[0] for r in front}, rejected


def similarity(a,b):
    return len(a & b)/len(a | b) if a or b else 1.0


def measured_rows(base, costs):
    return [(s,info,red,costs[s]) for s,info,red,_ in base]


def compare(h, timings, weights):
    n = len(weights)
    unit = objectives(h,(1,)*n)
    abstract = objectives(h,weights)
    med = {s:int(median(v)) for s,v in timings.items()}
    rows = measured_rows(unit[1:],med)
    report = []
    for k in range(1,n+1):
        pool = [r for r in rows if r[0].bit_count()==k]
        ids = [r[0] for r in pool]
        mf,rejected = front_ids(pool)
        assert mf == {r[0] for r in reference(pool)}
        uf,_ = front_ids([unit[s] for s in ids])
        af,_ = front_ids([abstract[s] for s in ids])
        trials = []
        for i in range(len(SEEDS)):
            sample = [(s,unit[s][1],unit[s][2],timings[s][i]) for s in ids]
            f,_ = front_ids(sample)
            trials.append(f)
        budget = k*n-k*(k-1)//2
        baselines = {}
        for method in ("static","greedy"):
            s = search(n,k,h,method,budget)["subset"]
            baselines[method] = {"subset":s,"on_median_frontier":s in mf,
                                "on_repeat_frontiers":sum(s in t for t in trials),
                                "median_dominance_witness":rejected.get(s)}
        stable = set.intersection(*trials)
        report.append({"rule_budget":k,"enumerated":len(pool),
                       "median_frontier":sorted(mf),"unit_frontier_size":len(uf),
                       "abstract_frontier_size":len(af),
                       "jaccard_median_unit":similarity(mf,uf),
                       "jaccard_median_abstract":similarity(mf,af),
                       "repeat_frontier_sizes":[len(t) for t in trials],
                       "repeat_jaccard_to_median":[similarity(t,mf) for t in trials],
                       "stable_all_repeat_frontier":sorted(stable),
                       "baselines":baselines})
    return report


def audit():
    names,raw,_ = freeze()
    n = len(raw)
    _,counts = partition(raw,DOMAIN)
    occupied = tuple((s,k) for s,k in enumerate(counts) if k)
    h = subset_entropies(counts,n)
    ids = list(range(1,1<<n))
    # Untimed full pass validates the materialized projection against V3.7.73.
    ledger = sha256()
    for s in ids:
        groups = project(occupied,s)
        assert sum(groups.values())==DOMAIN
        assert abs(entropy(groups,DOMAIN)-h[s])<=TOL
        ledger.update(json.dumps([s,sorted(groups.items())],
                      separators=(",",":")).encode())
    # Additional independent direct bitmap projection on predetermined masks.
    for s in sorted({1<<j for j in range(n)} | {3,5,7,255,(1<<n)-1}):
        indices = [j for j in range(n) if s>>j&1]
        _,direct = partition(tuple(raw[j] for j in indices),DOMAIN)
        expected = {sum(((i>>q)&1)<<j for q,j in enumerate(indices)):v
                    for i,v in enumerate(direct) if v}
        assert project(occupied,s)==expected

    timings = {s:[] for s in ids}
    # One warm pass above, then five complete randomized-order passes.
    # Clock only materialization, excluding entropy, checks, and setup.
    for seed in SEEDS:
        order = ids.copy()
        Random(seed).shuffle(order)
        for s in order:
            start = perf_counter_ns()
            groups = project(occupied,s)
            elapsed = perf_counter_ns()-start
            assert sum(groups.values())==DOMAIN
            assert abs(entropy(groups,DOMAIN)-h[s])<=TOL
            timings[s].append(elapsed)
    report = compare(h,timings,WEIGHTS)
    assert sum(r["enumerated"] for r in report)==4095
    return {"schema":"pl5-projection-cost-v3776-1","source":"INTERNAL/AI_AUTHORED",
            "domain":DOMAIN,"rule_names":names,"rule_mask_sha256":[digest(m) for m in raw],
            "projection_ledger_sha256":ledger.hexdigest(),
            "platform":platform.platform(),"python":platform.python_version(),
            "clock":"perf_counter_ns","seeds":SEEDS,"nonempty_full_atoms":len(occupied),
            "rows":report,
            "limitations":["timing is cached truth-signature projection only, not raw rule execution",
                "setup and entropy calculation excluded; no cross-machine speed claims",
                "five repeated timings are descriptive; no timing gate",
                "median front uses measured nonadditive cost, quantized information objectives",
                "frontier sensitivity may reflect measurement noise; no historical coverage"]},timings


class Tests(unittest.TestCase):
    def test_projection(self):
        occupied=((0,2),(1,3),(2,4),(3,1))
        self.assertEqual(project(occupied,1),{0:6,1:4})
        self.assertEqual(project(occupied,0),{0:10})
        self.assertEqual(project(occupied,3),dict(occupied))

    def test_cost_changes_front(self):
        h=subset_entropies([1]*4,2)
        timing={1:[20]*5,2:[10]*5,3:[30]*5}
        rows=compare(h,timing,(1,2))
        self.assertEqual(rows[0]["median_frontier"],[2])
        self.assertEqual(rows[0]["jaccard_median_abstract"],0)
        self.assertEqual(rows[0]["stable_all_repeat_frontier"],[2])

    def test_full(self):
        report,timing=audit()
        self.assertEqual(len(timing),4095)
        self.assertTrue(all(len(v)==5 for v in timing.values()))
        self.__class__.result=report,timing


if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    report,timing=Tests.result
    print("V3776_PROJECTION_JSON="+json.dumps(report,sort_keys=True))
    # Per-budget evidence lines keep each log record bounded.
    for k in range(1,13):
        print("V3776_TIMINGS_K"+str(k)+"="+json.dumps(
            [[s,v] for s,v in timing.items() if s.bit_count()==k],separators=(",",":")))
