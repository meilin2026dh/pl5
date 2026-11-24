"""V3.7.68: bounded partial-conjunction cache invalidation audit.
INTERNAL/AI_AUTHORED; synthetic rule changes; no historical records.
"""
from collections import OrderedDict
from hashlib import sha256
from random import Random
from statistics import median
from time import perf_counter_ns
import json
import platform
import unittest

from refined_atom_floor_v3762 import freeze, DOMAIN, digest

CAPACITY = 128
REPEATS = 7
STRATEGIES = ("fixed", "flush", "selective")


class Engine:
    def __init__(self, raw, size, mode, capacity=CAPACITY):
        assert mode in STRATEGIES and capacity >= 0
        self.full = (1 << size) - 1
        self.raw = tuple(raw)
        assert all(0 <= m <= self.full for m in self.raw)
        self.mode, self.capacity = mode, capacity
        self.cache = OrderedDict()
        self.hits = self.misses = self.evictions = self.invalidations = 0
        self.pairs = tuple((self.full ^ m, m) for m in self.raw)

    def update(self, raw):
        raw = tuple(raw)
        if len(raw) != len(self.raw) or any(m < 0 or m > self.full for m in raw):
            raise ValueError("invalid rule inventory")
        changed = sum(1 << j for j, (a,b) in enumerate(zip(self.raw,raw)) if a != b)
        if not changed:
            return
        if self.mode == "flush":
            self.invalidations += len(self.cache)
            self.cache.clear()
        elif self.mode == "selective":
            for key in tuple(self.cache):
                if (key[0] | key[1]) & changed:
                    del self.cache[key]
                    self.invalidations += 1
        self.raw = raw
        self.pairs = tuple((self.full ^ m,m) for m in raw)

    def query(self, key):
        pos, neg = key
        if pos < 0 or neg < 0 or pos & neg or (pos | neg) >= (1 << len(self.raw)):
            raise ValueError("invalid signed conjunction")
        if key in self.cache:
            self.hits += 1
            self.cache.move_to_end(key)
            return self.cache[key]
        self.misses += 1
        m = self.full
        for j,pair in enumerate(self.pairs):
            b = 1 << j
            if pos & b:
                m &= pair[1]
            elif neg & b:
                m &= pair[0]
            if not m:
                break
        if self.mode != "fixed" and self.capacity:
            self.cache[key] = m
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
                self.evictions += 1
        return m

    def counts(self):
        return dict(hits=self.hits, misses=self.misses, evictions=self.evictions,
                    invalidations=self.invalidations, retained_entries=len(self.cache))


def oracle(raw, size, key):
    pos, neg = key
    m = (1 << size)-1
    for j in reversed(range(len(raw))):
        if pos & (1 << j):
            m &= raw[j]
        elif neg & (1 << j):
            m &= ((1 << size)-1) ^ raw[j]
    return m


def all_keys(n):
    for v in range(3**n):
        pos = neg = 0
        for j in range(n):
            v, d = divmod(v,3)
            if d == 1: pos |= 1 << j
            if d == 2: neg |= 1 << j
        yield pos,neg


class Checks(unittest.TestCase):
    def test_exhaustive_toy(self):
        base = (0b10101010,0b11001100,0b10101010)
        for mode in STRATEGIES:
            e = Engine(base,8,mode,27)
            for raw in (base,(base[0]^3,base[1],base[2]),(0,255,0),base):
                e.update(raw)
                for key in all_keys(3):
                    expected = sum(1 << i for i in range(8)
                        if all(not ((key[0]|key[1]) >> j & 1)
                            or bool(raw[j] >> i & 1) == bool(key[0] >> j & 1)
                            for j in range(3)))
                    self.assertEqual(e.query(key),expected)
                    self.assertEqual(e.query(key),expected)
    def test_selective_and_lru(self):
        e = Engine((170,204),8,"selective",2)
        e.query((1,0)); e.query((0,2))
        e.update((171,204))
        self.assertEqual(list(e.cache),[(0,2)])
        self.assertEqual(e.invalidations,1)
        e.update((171,204))
        self.assertEqual(e.invalidations,1)
        e.query((1,0)); e.query((0,2)); e.query((0,0))
        self.assertEqual(list(e.cache),[(0,2),(0,0)])
        self.assertEqual(e.evictions,1)
        for bad in ((1,1),(4,0),(-1,0)):
            with self.assertRaises(ValueError): e.query(bad)
    def test_empty_and_zero_capacity(self):
        e = Engine((0,),8,"selective",0)
        self.assertEqual(e.query((1,0)),0)
        self.assertEqual(e.query((0,0)),255)
        self.assertEqual(len(e.cache),0)


def workload(raw, size, locality):
    # Deterministic synthetic requests, not selected by candidate counts.
    rng = Random(3768)
    n = len(raw)
    def key():
        pos = neg = 0
        for j in rng.sample(range(n),rng.choice((0,2,4,8,12))):
            if rng.randrange(2): pos |= 1 << j
            else: neg |= 1 << j
        return pos,neg
    hot = tuple(key() for _ in range(64))
    current = list(raw)
    epochs = []
    for i in range(8):
        if i:
            j = (i-1) % n
            # Deliberate, reproducible mutation; no source files changed.
            current[j] ^= 1 << ((i*7919) % size)
        queries = tuple(rng.choice(hot) if rng.randrange(100)<locality else key()
                        for _ in range(512))
        epochs.append((tuple(current),queries))
    return epochs


def run(raw, size, mode, epochs, expected):
    t = perf_counter_ns()
    e = Engine(raw,size,mode)
    setup = perf_counter_ns()-t
    updates = queries_ns = 0
    for (masks,queries),ref in zip(epochs,expected):
        t = perf_counter_ns()
        e.update(masks)
        updates += perf_counter_ns()-t
        t = perf_counter_ns()
        actual = tuple(e.query(k) for k in queries)
        queries_ns += perf_counter_ns()-t
        assert actual == ref
    return dict(setup_ns=setup,update_ns=updates,query_ns=queries_ns,
                total_ns=setup+updates+queries_ns,**e.counts())


def bench():
    _,raw,_ = freeze()
    assert len(raw)==12
    results = {}
    for locality in (0,90):
        epochs = workload(raw,DOMAIN,locality)
        expected = [tuple(oracle(m,DOMAIN,k) for k in q) for m,q in epochs]
        h = sha256()
        for (masks,keys),outputs in zip(epochs,expected):
            for m in masks: h.update(bytes.fromhex(digest(m)))
            for (p,n),m in zip(keys,outputs):
                h.update(p.to_bytes(2,"little")+n.to_bytes(2,"little"))
                h.update(bytes.fromhex(digest(m)))
        rows = {s:[] for s in STRATEGIES}
        for i in range(REPEATS):
            for s in STRATEGIES[i%3:]+STRATEGIES[:i%3]:
                rows[s].append(run(raw,DOMAIN,s,epochs,expected))
        for s, rr in rows.items():
            assert all(x["hits"]+x["misses"]==4096 for x in rr)
            assert all(x["retained_entries"]<=CAPACITY for x in rr)
        results[str(locality)] = dict(ledger_sha256=h.hexdigest(),
            candidate_count_min=min(m.bit_count() for ep in expected for m in ep),
            candidate_count_max=max(m.bit_count() for ep in expected for m in ep),
            strategies={s:dict(raw=rr,median_total_ns=int(median(x["total_ns"] for x in rr)))
                        for s,rr in rows.items()})
    return dict(schema="pl5-partial-cache-v3768-1",source="INTERNAL/AI_AUTHORED",
        platform=platform.platform(),domain=DOMAIN,capacity_entries=CAPACITY,
        epochs=8,queries_per_epoch=512,repeats=REPEATS,results=results,
        candidate_membership_preserved=True,historical_coverage_measured=False,
        limitations=["synthetic single-bit mutations and request locality",
        "partial conjunctions include unconstrained and large outputs, no cap imposed",
        "entry limit not byte limit; no RSS or serialized output measurement",
        "shared rule construction and oracle verification excluded from timing",
        "single-threaded in-process execution; timing observations not acceptance gates"])


if __name__ == "__main__":
    result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    if not result.wasSuccessful(): raise SystemExit(1)
    print("V3768_PARTIAL_CACHE_JSON="+json.dumps(bench(),sort_keys=True))
