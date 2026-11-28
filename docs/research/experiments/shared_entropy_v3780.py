"""V3.7.80: shared projection in the complete static combination audit.

INTERNAL/AI_AUTHORED. Hypothesis: shared marginalization reduces entropy
precomputation time without changing the Shapley, mutual-information or
Pareto ledgers. Measure total pipeline separately from precomputation.
No new filtering rules, historical records, or production changes.
"""
from hashlib import sha256
from math import fsum, log2
from random import Random
from statistics import median
from time import perf_counter_ns
import json
import platform
import unittest

from signed_order_v3763 import freeze, partition, DOMAIN, digest
from static_entropy_v3773 import subset_entropies, decompose
from static_pareto_v3775 import compare, WEIGHTS, SCALE
from projection_tree_v3779 import shared_sweep

SOURCE_HEAD = "407888519ec56afdf7a2c43aee1cd577b3e78a2c"


def shared_entropies(counts, n):
    """Same numerical expression and ordering as the independent reference."""
    if not 1 <= n <= 12 or len(counts) != 1 << n:
        raise ValueError("invalid bounded inventory")
    total = sum(counts)
    if total <= 0 or any(k < 0 for k in counts):
        raise ValueError("invalid counts")
    occupied = tuple((s,k) for s,k in enumerate(counts) if k)
    out = [None] * (1 << n)
    for subset, groups, _ in shared_sweep(occupied, n):
        assert out[subset] is None and sum(groups.values()) == total
        out[subset] = fsum(-k/total*log2(k/total)
                           for k in sorted(groups.values()))
    assert all(v is not None for v in out)
    return out


def downstream(h, n, weights):
    values, checks = decompose(h,n)
    pairs = [(i,j,h[1<<i]+h[1<<j]-h[(1<<i)|(1<<j)])
             for i in range(n) for j in range(i+1,n)]
    models = {"unit":compare(h,(1,)*n),
              "heterogeneous_abstract":compare(h,weights)}
    return {"values":values,"checks":checks,"pairs":pairs,"models":models}


def pipeline(method, counts, n, weights):
    start = perf_counter_ns()
    h = method(counts,n)
    middle = perf_counter_ns()
    result = downstream(h,n,weights)
    end = perf_counter_ns()
    return (h,result), {"precompute_ns":middle-start,
                        "downstream_ns":end-middle,"total_ns":end-start}


def canonical(payload):
    # Quantize floating-point descriptive fields for cross-platform ledger
    # comparison, separately from exact within-platform equality assertions.
    if isinstance(payload,float):
        return round(payload*SCALE)
    if isinstance(payload,dict):
        return {k:canonical(v) for k,v in payload.items()}
    if isinstance(payload,(list,tuple)):
        return [canonical(v) for v in payload]
    return payload


def fingerprint(payload):
    return sha256(json.dumps(canonical(payload),sort_keys=True,
                            separators=(",",":"),allow_nan=False).encode()).hexdigest()


def audit():
    names,masks,_ = freeze()
    n = len(masks)
    assert n == 12
    _,counts = partition(masks,DOMAIN)
    methods = {"independent":subset_entropies,"shared":shared_entropies}
    # Both full pipelines warmed once; exact equality includes every subset
    # entropy, rule allocation, pair value, frontier and witness ledger.
    reference,_ = pipeline(methods["independent"],counts,n,WEIGHTS)
    alternative,_ = pipeline(methods["shared"],counts,n,WEIGHTS)
    assert reference == alternative
    trials = []
    for i in range(4):
        order = tuple(methods) if i % 2 == 0 else tuple(reversed(methods))
        row = {"order":order}
        for label in order:
            result,timings = pipeline(methods[label],counts,n,WEIGHTS)
            assert result == reference
            row[label] = timings
        trials.append(row)
    ratios = {phase:median(t["independent"][phase]/max(1,t["shared"][phase])
                           for t in trials)
              for phase in ("precompute_ns","downstream_ns","total_ns")}
    h,report = reference
    return {"schema":"pl5-shared-entropy-v3780-1","source":"INTERNAL/AI_AUTHORED",
            "source_head":SOURCE_HEAD,"domain":DOMAIN,"rule_names":names,
            "rule_mask_sha256":[digest(m) for m in masks],
            "subsets":len(h),"exact_within_platform_equality":True,
            "entropy_ledger_sha256":fingerprint(h),
            "downstream_ledger_sha256":fingerprint(report),
            "frontier_counts":{k:[r["frontier_size"] for r in v]
                               for k,v in report["models"].items()},
            "shapley_bits":[v["shapley_bits"] for v in report["values"]],
            "paired_trials":trials,"median_paired_ratios":ratios,
            "platform":platform.platform(),"python":platform.python_version(),
            "limitations":[
                "same fixed static partition; no historical coverage or new filtering rules",
                "total pipeline includes exact Pareto reference and Shapley audits",
                "common freeze and partition construction excluded from timing",
                "four paired warm runs; descriptive times, no timing gate",
                "ledger float quantization 1e-8; within-platform equality is exact",
                "no measured peak memory or complete filtering execution cost"]}


class Tests(unittest.TestCase):
    def test_sparse_dense_and_duplicate(self):
        rng = Random(3780)
        for n in range(1,7):
            for counts in ([1]*(1<<n),[9]+[0]*((1<<n)-1),
                           [rng.randrange(1,5) for _ in range(1<<n)]):
                self.assertEqual(shared_entropies(counts,n),subset_entropies(counts,n))
        counts=[1,0,0,1,1,0,0,1]
        a,_=pipeline(subset_entropies,counts,3,(1,2,3))
        b,_=pipeline(shared_entropies,counts,3,(1,2,3))
        self.assertEqual(a,b)
        self.assertEqual(a[1]["values"][0]["shapley_bits"],0.5)

    def test_invalid(self):
        for counts,n in (([0,0],1),([1,-1],1),([1],1),([1],0)):
            with self.assertRaises(ValueError):
                shared_entropies(counts,n)

    def test_full(self):
        report=audit()
        self.assertEqual(report["subsets"],4096)
        self.assertEqual(len(report["paired_trials"]),4)
        self.assertTrue(report["exact_within_platform_equality"])
        self.__class__.result=report


if __name__ == "__main__":
    if not unittest.TextTestRunner().run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
            ).wasSuccessful():
        raise SystemExit(1)
    print("V3780_SHARED_ENTROPY_JSON="+json.dumps(Tests.result,sort_keys=True,allow_nan=False))
