"""V3.7.79: exact shared marginalization for full subset projection sweeps.

INTERNAL/AI_AUTHORED. Fixed static partition; no new rule masks or historical
records. Hypothesis: reuse of immediate parent groups reduces dictionary-entry
visits for a complete sweep, preserving every projected group exactly.
"""
from hashlib import sha256
import json
import platform
from random import Random
from time import perf_counter_ns
from statistics import median
import unittest

from signed_order_v3763 import freeze, partition, DOMAIN, digest
from projection_cost_v3776 import project

SOURCE_HEAD = "a82fdfcf6bae2d7fc5d3b33971ea648b02670941"


def shared_sweep(occupied, n):
    """Yield (subset, groups, input-entry visits); output maps are read-only.

    Remove bits in strictly increasing index order along each path. Every
    subset has a unique path from the full set (its sorted missing bits).
    Marginalizing a parent map is exact by associativity of integer sums.
    Only the current recursion path needs to be retained by the generator.
    """
    if not 1 <= n <= 12:
        raise ValueError("bounded inventory required")
    root = dict(occupied)
    def walk(subset, groups, start, visits):
        yield subset, groups, visits
        for j in range(start, n):
            bit = 1 << j
            child = {}
            for key, count in groups.items():
                k = key & ~bit
                child[k] = child.get(k, 0) + count
            yield from walk(subset ^ bit, child, j + 1, len(groups))
    yield from walk((1 << n)-1, root, 0, len(occupied))


def independent_sweep(occupied, n):
    for subset in range(1 << n):
        yield subset, project(occupied, subset), len(occupied)


def compare(occupied, n):
    total = sum(k for _, k in occupied)
    fingerprints = [None] * (1 << n)
    visits = output_groups = 0
    rows = [[0, 0, 0] for _ in range(n+1)]
    for subset, groups, work in shared_sweep(occupied, n):
        if fingerprints[subset] is not None:
            raise AssertionError("duplicate subset")
        expected = project(occupied, subset)
        assert groups == expected and sum(groups.values()) == total
        fingerprints[subset] = sha256(json.dumps(
            [subset, sorted(groups.items())], separators=(",", ":")
        ).encode()).hexdigest()
        visits += work
        output_groups += len(groups)
        row = rows[subset.bit_count()]
        row[0] += 1
        row[1] += len(occupied)
        row[2] += work
    assert all(x is not None for x in fingerprints)
    baseline = (1 << n) * len(occupied)
    assert visits <= baseline
    return {"subsets": len(fingerprints),
            "baseline_entry_visits": baseline,
            "shared_entry_visits": visits,
            "visit_reduction_fraction": 1-visits/baseline if baseline else 0,
            "output_groups": output_groups,
            "projection_sha256": sha256("".join(fingerprints).encode()).hexdigest(),
            "per_rule_budget": [
                {"budget": k, "subsets": v[0], "baseline_visits": v[1],
                 "shared_visits": v[2]} for k,v in enumerate(rows)]}


def consume(sweep, occupied, n):
    # Same lightweight streaming consumer for both implementations.
    count = groups_total = visits = 0
    for _, groups, work in sweep(occupied, n):
        count += 1
        groups_total += len(groups)
        visits += work
    return count, groups_total, visits


def audit():
    names, masks, _ = freeze()
    n = len(masks)
    assert n == 12
    _, counts = partition(masks, DOMAIN)
    occupied = tuple((s,k) for s,k in enumerate(counts) if k)
    report = compare(occupied, n)
    assert report["subsets"] == 4096
    assert report["shared_entry_visits"] < report["baseline_entry_visits"]
    expected = {
        "independent": (report["subsets"], report["output_groups"],
                        report["baseline_entry_visits"]),
        "shared": (report["subsets"], report["output_groups"],
                   report["shared_entry_visits"])}
    methods = {"independent": independent_sweep, "shared": shared_sweep}
    for label, method in methods.items():
        assert consume(method, occupied, n) == expected[label]
    # Fixed paired alternating order, complete sweeps; setup and exact
    # equality checks excluded. No timing-based acceptance gate.
    trials = []
    for i in range(6):
        order = tuple(methods) if i % 2 == 0 else tuple(reversed(methods))
        row = {"order": order}
        for label in order:
            t0 = perf_counter_ns()
            result = consume(methods[label], occupied, n)
            row[label+"_ns"] = perf_counter_ns()-t0
            assert result == expected[label]
        trials.append(row)
    return dict(report, schema="pl5-projection-tree-v3779-1",
        source="INTERNAL/AI_AUTHORED", source_head=SOURCE_HEAD,
        rule_names=names, rule_mask_sha256=[digest(m) for m in masks],
        domain=DOMAIN, occupied_atoms=len(occupied),
        platform=platform.platform(), python=platform.python_version(),
        paired_trials=trials,
        median_paired_ratio=median(
            r["independent_ns"]/max(1,r["shared_ns"]) for r in trials),
        limitations=[
            "complete subset sweep including empty subset, not single queries",
            "entry visits are semantic counts, not CPU instructions",
            "recursion overhead and allocation included in sweep timing",
            "partition setup and exact equality checks excluded from timing",
            "streaming consumer; no full output cache or measured peak memory",
            "timings descriptive within platform; no historical coverage"])


class Tests(unittest.TestCase):
    def test_sparse_and_dense_toy(self):
        rng = Random(3779)
        for n in range(1, 7):
            for counts in ([1]*(1<<n),
                           [5]+[0]*((1<<n)-1),
                           [rng.randrange(4) for _ in range(1<<n)]):
                occupied = tuple((s,k) for s,k in enumerate(counts) if k)
                r = compare(occupied,n)
                self.assertEqual(r["subsets"],1<<n)
                self.assertLessEqual(r["shared_entry_visits"],
                                     r["baseline_entry_visits"])
                maps = dict((s,g) for s,g,_ in shared_sweep(occupied,n))
                for s,g in maps.items():
                    # Independent direct aggregation from each original cell.
                    direct = {}
                    for x,c in enumerate(counts):
                        if c:
                            key = x & s
                            direct[key] = direct.get(key,0)+c
                    self.assertEqual(g,direct)

    def test_bound(self):
        for n in (0,13):
            with self.assertRaises(ValueError):
                list(shared_sweep(((0,1),),n))

    def test_full(self):
        r = audit()
        self.assertEqual(r["subsets"],4096)
        self.assertEqual(len(r["paired_trials"]),6)
        self.__class__.result = r


if __name__ == "__main__":
    if not unittest.TextTestRunner().run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
            ).wasSuccessful():
        raise SystemExit(1)
    print("V3779_TREE_JSON="+json.dumps(Tests.result,sort_keys=True,allow_nan=False))
