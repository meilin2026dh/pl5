"""V3.7.70: byte-budgeted partial filter cache and prefix reuse.
INTERNAL/AI_AUTHORED; fixed development workloads, no historical input.
Budget counts serialized bitmap payload + four-byte signed key only.
Python object/allocator overhead and transient outputs are NOT bounded.
"""
from collections import OrderedDict
from hashlib import sha256
from random import Random
from statistics import median
from time import perf_counter_ns
import json
import platform
import unittest

from partial_cache_v3768 import oracle, all_keys, workload
from refined_atom_floor_v3762 import freeze, DOMAIN, digest

BUDGET = 256 * 1024
REPEATS = 3
MODES = ("fixed", "exact", "prefix")


class Cache:
    def __init__(self, budget):
        if budget < 0:
            raise ValueError("negative budget")
        self.budget = budget
        self.data = OrderedDict()
        self.used = self.peak = self.evictions = self.invalidations = self.skipped = 0

    def get(self, key):
        if key not in self.data:
            return None
        self.data.move_to_end(key)
        return int.from_bytes(self.data[key], "little")

    def remove(self, key):
        self.used -= 4 + len(self.data.pop(key))

    def put(self, key, value):
        length = (value.bit_length() + 7) // 8
        size = 4 + length
        if size > self.budget:
            self.skipped += 1
            return
        if key in self.data:
            self.remove(key)
        while self.used + size > self.budget:
            self.remove(next(iter(self.data)))
            self.evictions += 1
        self.data[key] = value.to_bytes(length, "little")
        self.used += size
        self.peak = max(self.peak, self.used)
        assert 0 <= self.used <= self.budget

    def invalidate(self, changed):
        for key in tuple(self.data):
            if (key[0] | key[1]) & changed:
                self.remove(key)
                self.invalidations += 1

    def check(self):
        assert self.used == sum(4 + len(v) for v in self.data.values())
        assert self.peak <= self.budget


class Engine:
    def __init__(self, raw, size, mode, budget=BUDGET):
        if mode not in MODES or not 0 <= len(raw) <= 16:
            raise ValueError("invalid mode or inventory")
        self.full = (1 << size) - 1
        self.raw = tuple(raw)
        if any(not 0 <= x <= self.full for x in self.raw):
            raise ValueError("invalid bitmap")
        self.pairs = tuple((self.full ^ m, m) for m in self.raw)
        self.mode = mode
        self.cache = Cache(budget)
        self.exact_hits = self.prefix_hits = self.queries = self.intersections = 0

    def update(self, raw):
        raw = tuple(raw)
        if len(raw) != len(self.raw) or any(not 0 <= m <= self.full for m in raw):
            raise ValueError("invalid update")
        changed = sum(1 << i for i, (a, b) in enumerate(zip(self.raw, raw)) if a != b)
        if changed:
            self.cache.invalidate(changed)
            self.raw = raw
            self.pairs = tuple((self.full ^ m, m) for m in raw)

    def apply(self, m, p, n):
        bits = p | n
        while bits and m:
            b = bits & -bits
            m &= self.pairs[b.bit_length() - 1][bool(p & b)]
            self.intersections += 1
            bits ^= b
        return m

    def query(self, key):
        p, n = key
        if p < 0 or n < 0 or p & n or (p | n) >= 1 << len(self.raw):
            raise ValueError("invalid key")
        self.queries += 1
        if self.mode != "fixed":
            value = self.cache.get(key)
            if value is not None:
                self.exact_hits += 1
                return value
        m = self.full
        bits = p | n
        if self.mode == "prefix" and bits.bit_count() >= 4:
            # Frozen policy: first two active rules in ascending order.
            b = bits & -bits
            rest = bits ^ b
            prefix = b | (rest & -rest)
            pk = (p & prefix, n & prefix)
            value = self.cache.get(pk)
            if value is None:
                value = self.apply(m, *pk)
                self.cache.put(pk, value)
            else:
                self.prefix_hits += 1
            m = value
            p, n = p & ~prefix, n & ~prefix
        m = self.apply(m, p, n)
        if self.mode != "fixed":
            self.cache.put(key, m)
        return m

    def counts(self):
        self.cache.check()
        return dict(queries=self.queries, exact_hits=self.exact_hits,
                    prefix_hits=self.prefix_hits, intersections=self.intersections,
                    retained_bytes=self.cache.used, peak_bytes=self.cache.peak,
                    retained_entries=len(self.cache.data), evictions=self.cache.evictions,
                    invalidations=self.cache.invalidations, skipped=self.cache.skipped)


def shared_prefix_workload(raw, size):
    # Deliberately favorable synthetic workload; not a representative sample.
    # Fixed two-rule prefix with independently sampled suffix, no output selection.
    rng = Random(3770)
    epochs = []
    masks = list(raw)
    for epoch in range(8):
        if epoch:
            masks[(epoch - 1) % len(raw)] ^= 1 << ((epoch * 7919) % size)
        keys = []
        for _ in range(512):
            p, n = 1, 2
            for j in rng.sample(range(2, len(raw)), 6):
                if rng.randrange(2):
                    p |= 1 << j
                else:
                    n |= 1 << j
            keys.append((p, n))
        epochs.append((tuple(masks), tuple(keys)))
    return epochs


class Checks(unittest.TestCase):
    def test_all_signed_keys_mutations_and_budgets(self):
        base = (0b10101010, 0b11001100, 0b11110000, 0b10101010)
        for mode in MODES:
            for budget in (0, 4, 9, 1000):
                e = Engine(base, 8, mode, budget)
                for raw in (base, (0, 255, 0, 255), base):
                    e.update(raw)
                    for p, n in all_keys(4):
                        expected = sum(1 << i for i in range(8)
                            if all(not ((p | n) >> j & 1) or
                                bool(raw[j] >> i & 1) == bool(p >> j & 1)
                                for j in range(4)))
                        self.assertEqual(e.query((p, n)), expected)
                        self.assertEqual(e.query((p, n)), expected)
                        e.cache.check()

    def test_budget_eviction_and_zero(self):
        c = Cache(9)
        c.put((1, 0), 0)
        c.put((0, 1), 255)
        self.assertEqual(c.used, 9)
        self.assertEqual(c.get((1, 0)), 0)
        c.put((2, 0), 65535)
        self.assertEqual(c.used, 6)
        self.assertEqual(c.evictions, 2)
        c.put((4, 0), 1 << 100)
        self.assertEqual(c.skipped, 1)
        c.invalidate(2)
        self.assertEqual(c.used, 0)
        c.check()

    def test_prefix_reuse_and_dependency(self):
        raw = (170, 204, 240, 255, 255)
        e = Engine(raw, 8, "prefix", 100)
        self.assertEqual(e.query((15, 0)), oracle(raw, 8, (15, 0)))
        self.assertEqual(e.query((23, 0)), oracle(raw, 8, (23, 0)))
        self.assertEqual(e.prefix_hits, 1)
        e.update((170, 204, 240, 0, 255))
        self.assertIn((3, 0), e.cache.data)
        self.assertNotIn((15, 0), e.cache.data)
        self.assertIn((23, 0), e.cache.data)
        e.update((0, 204, 240, 0, 255))
        self.assertFalse(e.cache.data)

    def test_invalid(self):
        e = Engine((1,), 8, "prefix")
        for key in ((1, 1), (-1, 0), (2, 0)):
            with self.assertRaises(ValueError):
                e.query(key)
        with self.assertRaises(ValueError):
            e.update((256,))


def run(raw, epochs, expected, mode):
    t = perf_counter_ns()
    e = Engine(raw, DOMAIN, mode)
    setup = perf_counter_ns() - t
    update = query = 0
    for (masks, keys), ref in zip(epochs, expected):
        t = perf_counter_ns()
        e.update(masks)
        update += perf_counter_ns() - t
        t = perf_counter_ns()
        actual = tuple(e.query(k) for k in keys)
        query += perf_counter_ns() - t
        assert actual == ref
    return dict(setup_ns=setup, update_ns=update, query_ns=query,
                total_ns=setup+update+query, **e.counts())


def bench():
    _, raw, _ = freeze()
    assert len(raw) == 12
    results = {}
    for name, epochs in (
        ("low", workload(raw, DOMAIN, 0)),
        ("high", workload(raw, DOMAIN, 90)),
        ("shared_prefix", shared_prefix_workload(raw, DOMAIN)),
    ):
        expected = [tuple(oracle(m, DOMAIN, k) for k in q) for m, q in epochs]
        h = sha256()
        for (masks, keys), outputs in zip(epochs, expected):
            for m in masks:
                h.update(bytes.fromhex(digest(m)))
            for (p, n), m in zip(keys, outputs):
                h.update(p.to_bytes(2, "little") + n.to_bytes(2, "little"))
                h.update(bytes.fromhex(digest(m)))
        rows = {mode: [] for mode in MODES}
        for i in range(REPEATS):
            for mode in MODES[i:] + MODES[:i]:
                rows[mode].append(run(raw, epochs, expected, mode))
        for rr in rows.values():
            assert all(r["queries"] == 4096 and r["peak_bytes"] <= BUDGET for r in rr)
            counts = [{k: v for k, v in r.items() if not k.endswith("_ns")} for r in rr]
            assert all(c == counts[0] for c in counts)
        results[name] = dict(ledger_sha256=h.hexdigest(),
            strategies={mode: dict(raw=rr, median_total_ns=int(median(
                r["total_ns"] for r in rr))) for mode, rr in rows.items()})
    return dict(schema="pl5-byte-prefix-cache-v3770-1", source="INTERNAL/AI_AUTHORED",
                platform=platform.platform(), domain=DOMAIN, budget_bytes=BUDGET,
                accounted_bytes="serialized variable-width bitmap plus four-byte key",
                repeats=REPEATS, queries_per_run=4096, results=results,
                candidate_membership_preserved=True, historical_coverage_measured=False,
                limitations=["not total process memory, excludes object overhead and transient outputs",
                    "development workloads; shared prefix deliberately favorable",
                    "single-threaded; no output transport; oracle and common freeze excluded",
                    "no timing gate; no policy tuning; no general performance claim"])


if __name__ == "__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks)).wasSuccessful():
        raise SystemExit(1)
    print("V3770_BYTE_PREFIX_JSON=" + json.dumps(bench(), sort_keys=True))
