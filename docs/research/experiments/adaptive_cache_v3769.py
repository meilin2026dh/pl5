"""V3.7.69: causal adaptive cache policy cost audit.
INTERNAL/AI_AUTHORED; synthetic workloads; no historical records.
"""
import json
import platform
import unittest
from hashlib import sha256
from statistics import median
from time import perf_counter_ns

from partial_cache_v3768 import (
    Engine, Checks, workload, oracle, all_keys, freeze, DOMAIN, digest, CAPACITY
)

WINDOW = 128
MIN_HITS = 45
BYPASS = 256
REPEATS = 3
MODES = ("fixed", "selective", "adaptive")


class Adaptive(Engine):
    """Observe past hits only; periodic bounded probes after bypass."""
    def __init__(self, raw, size, capacity=CAPACITY):
        super().__init__(raw, size, "selective", capacity)
        self.seen = self.window_hits = self.remaining = 0
        self.bypass_queries = self.policy_clears = self.disabled = self.enabled = 0

    def query(self, key):
        if self.remaining:
            result = super().query(key)
            self.bypass_queries += 1
            self.remaining -= 1
            if not self.remaining:
                self.mode = "selective"
                self.enabled += 1
            return result
        before = self.hits
        result = super().query(key)
        self.seen += 1
        self.window_hits += self.hits - before
        if self.seen == WINDOW:
            if self.window_hits < MIN_HITS:
                self.policy_clears += len(self.cache)
                self.cache.clear()
                self.mode = "fixed"
                self.remaining = BYPASS
                self.disabled += 1
            self.seen = self.window_hits = 0
        return result

    def counts(self):
        return dict(super().counts(), bypass_queries=self.bypass_queries,
                    policy_clears=self.policy_clears, disabled=self.disabled,
                    enabled=self.enabled)


class PolicyChecks(unittest.TestCase):
    def test_switch_and_update(self):
        raw = (170, 204, 240, 15, 51)
        e = Adaptive(raw, 8)
        keys = tuple(all_keys(5))
        for key in keys[:WINDOW]:
            self.assertEqual(e.query(key), oracle(raw, 8, key))
        self.assertEqual(e.disabled, 1)
        self.assertEqual(len(e.cache), 0)
        self.assertEqual(e.remaining, BYPASS)
        raw = (171, 204, 240, 15, 51)
        e.update(raw)
        for i in range(BYPASS):
            key = keys[i % len(keys)]
            self.assertEqual(e.query(key), oracle(raw, 8, key))
        self.assertEqual(e.enabled, 1)
        self.assertEqual(e.bypass_queries, BYPASS)
        for _ in range(2 * WINDOW):
            self.assertEqual(e.query((1, 0)), 171)
        self.assertEqual(e.disabled, 1)
        e.update((170, 204, 240, 15, 51))
        self.assertEqual(e.query((1, 0)), 170)
        for bad in ((1, 1), (32, 0), (-1, 0)):
            with self.assertRaises(ValueError):
                e.query(bad)

    def test_zero_capacity(self):
        e = Adaptive((170,), 8, 0)
        for i in range(2 * (WINDOW + BYPASS)):
            self.assertEqual(e.query((1, 0)), 170)
        self.assertEqual(e.disabled, 2)
        self.assertEqual(e.enabled, 2)
        self.assertEqual(len(e.cache), 0)


def run(raw, epochs, expected, mode):
    t = perf_counter_ns()
    e = Adaptive(raw, DOMAIN) if mode == "adaptive" else Engine(raw, DOMAIN, mode)
    setup = perf_counter_ns() - t
    phases = []
    for (masks, keys), ref in zip(epochs, expected):
        before = e.counts()
        t = perf_counter_ns()
        e.update(masks)
        update = perf_counter_ns() - t
        t = perf_counter_ns()
        actual = tuple(e.query(key) for key in keys)
        query = perf_counter_ns() - t
        assert actual == ref
        after = e.counts()
        assert after["retained_entries"] <= CAPACITY
        delta = {k: after[k] - before[k] for k in after if k != "retained_entries"}
        assert delta["hits"] + delta["misses"] == len(keys)
        phases.append(dict(update_ns=update, query_ns=query, **delta,
                           retained_entries=after["retained_entries"]))
    return dict(setup_ns=setup, phases=phases, counts=e.counts(),
                total_ns=setup + sum(p["update_ns"] + p["query_ns"] for p in phases))


def bench():
    _, raw, _ = freeze()
    assert len(raw) == 12
    low, high = workload(raw, DOMAIN, 0), workload(raw, DOMAIN, 90)
    assert all(a[0] == b[0] for a, b in zip(low, high))
    # Fixed scenarios, no tuning against these observations.
    scenarios = {"low": [0]*8, "high": [1]*8,
                 "low_to_high": [0]*4+[1]*4,
                 "high_to_low": [1]*4+[0]*4}
    results = {}
    for name, schedule in scenarios.items():
        epochs = [(low, high)[v][i] for i, v in enumerate(schedule)]
        expected = [tuple(oracle(m, DOMAIN, k) for k in q) for m, q in epochs]
        h = sha256()
        for (masks, keys), outputs in zip(epochs, expected):
            for mask in masks:
                h.update(bytes.fromhex(digest(mask)))
            for (p, n), mask in zip(keys, outputs):
                h.update(p.to_bytes(2, "little") + n.to_bytes(2, "little"))
                h.update(bytes.fromhex(digest(mask)))
        rows = {s: [] for s in MODES}
        for i in range(REPEATS):
            for s in MODES[i:] + MODES[:i]:
                rows[s].append(run(raw, epochs, expected, s))
        for rr in rows.values():
            assert all(r["counts"] == rr[0]["counts"] for r in rr)
            assert all(r["counts"]["hits"]+r["counts"]["misses"] == 4096 for r in rr)
        results[name] = dict(schedule=schedule, ledger_sha256=h.hexdigest(),
            strategies={s: dict(raw=rr, median_total_ns=int(median(r["total_ns"] for r in rr)))
                        for s, rr in rows.items()})
    return dict(schema="pl5-adaptive-cache-v3769-1", source="INTERNAL/AI_AUTHORED",
        platform=platform.platform(), domain=DOMAIN, capacity_entries=CAPACITY,
        window=WINDOW, min_hits=MIN_HITS, bypass=BYPASS, repeats=REPEATS,
        total_timed_queries=4*3*REPEATS*4096, results=results,
        candidate_membership_preserved=True, historical_coverage_measured=False,
        limitations=["fixed heuristic, no parameter sweep",
        "same result-entry cap, adaptive has extra scalar metadata; not a byte budget",
        "synthetic scenarios reuse V3.7.68 development workload; no independent workload claim",
        "cold rule freeze, oracle, RSS, serialization and concurrency excluded",
        "timings observational; three rotated repeats; retain unfavorable results"])


if __name__ == "__main__":
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(Checks),
                               unittest.defaultTestLoader.loadTestsFromTestCase(PolicyChecks)])
    if not unittest.TextTestRunner().run(suite).wasSuccessful():
        raise SystemExit(1)
    print("V3769_ADAPTIVE_CACHE_JSON=" + json.dumps(bench(), sort_keys=True))
