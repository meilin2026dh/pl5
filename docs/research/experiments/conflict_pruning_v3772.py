"""V3.7.72: exact conflict-core pruning versus direct bitmap pruning.
INTERNAL/AI_AUTHORED; static frozen masks; no historical records.
"""
from array import array
from time import perf_counter_ns
from hashlib import sha256
import json
import unittest

from signed_order_v3763 import freeze, partition, ternary_counts, literals, DOMAIN, CAP, digest, vector_digest
from minimal_conflict_v3771 import cores_and_closure, direct

MODES = ("exhaustive", "pair_core", "full_core", "bitmap_empty")


def index_cores(cores, powers, limit):
    # A newly contained core must include the most recently assigned literal.
    index = {}
    for state in cores:
        parts = tuple(literals(state, powers))
        if len(parts) > limit:
            continue
        mask = sum(1 << (2*j + int(p == 2*powers[j])) for j,p in parts)
        j,p = parts[-1]
        index.setdefault((j, int(p == 2*powers[j])), []).append(mask)
    return index


def search(raw, size, mode, index):
    n = len(raw)
    powers = tuple(3**j for j in range(n))
    full = (1 << size) - 1
    signed = tuple((full ^ m, m) for m in raw)
    output = array("I", [0]) * (3**n)
    stats = dict(nodes=0, intersections=0, core_checks=0, pruned_subtrees=0,
                 pruned_leaves=0, evaluated_leaves=0)
    def visit(j, state, selected, current):
        stats["nodes"] += 1
        if j == n:
            stats["evaluated_leaves"] += 1
            output[state] = current.bit_count()
            return
        visit(j+1, state, selected, current)
        for truth, rule in enumerate(signed[j]):
            bits = selected | (1 << (2*j+truth))
            if mode in ("pair_core", "full_core"):
                conflict = False
                for core in index.get((j,truth), ()):
                    stats["core_checks"] += 1
                    if bits & core == core:
                        conflict = True
                        break
                if conflict:
                    stats["pruned_subtrees"] += 1
                    stats["pruned_leaves"] += 3**(n-j-1)
                    continue
            stats["intersections"] += 1
            next_mask = current & rule
            if mode == "bitmap_empty" and not next_mask:
                stats["pruned_subtrees"] += 1
                stats["pruned_leaves"] += 3**(n-j-1)
                continue
            visit(j+1, state+(truth+1)*powers[j], bits, next_mask)
    visit(0, 0, 0, full)
    assert stats["evaluated_leaves"] + stats["pruned_leaves"] == 3**n
    return output, stats


def audit(raw, size, repeats=3):
    # Partition-derived count oracle is outside all timed search runs.
    _, atoms = partition(raw, size)
    powers, oracle = ternary_counts(atoms, len(raw))
    start = perf_counter_ns()
    cores, _ = cores_and_closure(oracle, powers)
    discovery_ns = perf_counter_ns()-start
    indexes, setup = {}, {}
    for mode, limit in (("pair_core",2),("full_core",len(raw))):
        start = perf_counter_ns()
        indexes[mode] = index_cores(cores,powers,limit)
        setup[mode] = perf_counter_ns()-start
    results = {mode: {"times_ns": []} for mode in MODES}
    for run in range(repeats):
        for mode in MODES[run%len(MODES):]+MODES[:run%len(MODES)]:
            start = perf_counter_ns()
            out, stats = search(raw,size,mode,indexes.get(mode,{}))
            elapsed = perf_counter_ns()-start
            assert out == oracle
            row = results[mode]
            if "counts" in row:
                assert row["counts"] == stats
            row["counts"] = stats
            row["times_ns"].append(elapsed)
    return {"source":"INTERNAL/AI_AUTHORED","domain":size,
            "states":len(oracle),"core_count":len(cores),
            "nonempty_at_cap":sum(0<k<=CAP for k in oracle),
            "counts_sha256":vector_digest(oracle),
            "rule_mask_sha256":[digest(m) for m in raw],
            "offline_core_discovery_ns":discovery_ns,
            "index_setup_ns":setup,"strategies":results,
            "limitations":["fixed rule order and full ternary search",
              "timed output is count ledger, not candidate serialization",
              "oracle construction excluded; core discovery and index setup separately recorded",
              "no timing gate; no historical coverage measured"]}


class Tests(unittest.TestCase):
    def test_toy_exact_membership(self):
        for raw,size in (((3,6,5),3), ((0,15,3,5),4), ((3,3,5),3)):
            _, atoms = partition(raw,size)
            powers, counts = ternary_counts(atoms,len(raw))
            cores,_ = cores_and_closure(counts,powers)
            expected = [direct(s,raw,size,powers).bit_count() for s in range(len(counts))]
            for mode in MODES:
                index = index_cores(cores,powers,2 if mode=="pair_core" else len(raw))
                out,stats = search(raw,size,mode,index)
                self.assertEqual(list(out),expected)
                self.assertEqual(stats["evaluated_leaves"]+stats["pruned_leaves"],len(counts))
    def test_three_way(self):
        r = audit((3,6,5),3,1)
        s = r["strategies"]
        self.assertGreater(s["full_core"]["counts"]["pruned_leaves"],s["pair_core"]["counts"]["pruned_leaves"])
        self.assertEqual(s["full_core"]["counts"]["pruned_leaves"],s["bitmap_empty"]["counts"]["pruned_leaves"])
    def test_frozen(self):
        _,raw,_ = freeze()
        r = audit(raw,DOMAIN)
        self.assertEqual(r["states"],531441)
        self.assertEqual(r["core_count"],668)
        self.assertEqual(r["nonempty_at_cap"],135641)
        self.assertEqual(r["strategies"]["full_core"]["counts"]["pruned_leaves"],199081)
        self.__class__.result = r


if __name__ == "__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3772_PRUNING_JSON="+json.dumps(Tests.result,sort_keys=True))
