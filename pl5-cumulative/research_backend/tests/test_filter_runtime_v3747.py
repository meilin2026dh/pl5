"""Bounded INTERNAL/AI_AUTHORED timing experiment on frozen filter masks.

Timing observations are diagnostic, never pass/fail performance thresholds.
"""
from hashlib import sha256
import json
import platform
from statistics import median
from time import perf_counter_ns

import numpy as np
import pytest

from pailie5.affine_recurrence_filters_v3739 import recurrence_keep_masks
from pailie5.high_throughput_v3714 import mask_from_bitmap
from pailie5.weighted_filter_order_v3746 import audit_weighted_order

DOMAIN = 100_000
WIDTH = DOMAIN // 8
FULL = (1 << DOMAIN) - 1
REPEATS = 5


def acquire(m):
    masks = tuple(recurrence_keep_masks())
    if m == 12:
        # Deliberately redundant supersets, for bounded planner-scaling
        # stress only; not new candidate filtering rules.
        masks += tuple(
            masks[i % 3] | int.from_bytes(bytes([p]) * WIDTH, "little")
            for i, p in enumerate((1, 2, 4, 8, 16, 32, 64, 128, 85))
        )
    return masks


def greedy(masks):
    left = list(range(len(masks)))
    active = FULL
    order = []
    while left:
        i = min(left, key=lambda j: ((active & masks[j]).bit_count(), j))
        left.remove(i)
        order.append(i)
        active &= masks[i]
    return tuple(order)


def exact(masks):
    result = audit_weighted_order(masks, (1,) * len(masks))
    return tuple(result["optimal"]["order"])


def bitmap_execute(masks, order):
    active = FULL
    for i in order:
        active &= masks[i]
        if not active:
            break
    return tuple(int(n) for n in np.flatnonzero(mask_from_bitmap(active)))


def scalar_execute(masks, order):
    # A fixed-cost byte-membership implementation of the scalar model.
    # Packing is part of execution time; this is not a raw deferred predicate.
    packed = tuple(x.to_bytes(WIDTH, "little") for x in masks)
    active = range(DOMAIN)
    probes = 0
    for i in order:
        b = packed[i]
        probes += len(active)
        active = [n for n in active if b[n >> 3] & (1 << (n & 7))]
        if not active:
            break
    return tuple(active), probes


def constructive_oracle():
    expected = []
    for a in range(10):
        for b in range(10):
            digits = [a, b]
            for _ in range(3):
                digits.append((digits[-2] + digits[-1]) % 10)
            expected.append(int("".join(map(str, digits))))
    return tuple(sorted(expected))


def run_once(m, frozen, cached_order, mode, plan, executor):
    start = perf_counter_ns()
    masks = acquire(m) if mode == "cold" else frozen
    acquired = perf_counter_ns()
    if plan == "input":
        order = tuple(range(m))
    elif plan == "count":
        order = tuple(sorted(range(m), key=lambda i: (masks[i].bit_count(), i)))
    elif plan == "greedy":
        order = greedy(masks)
    elif plan == "exact":
        order = exact(masks)
    elif plan == "cached_exact":
        order = cached_order
    else:
        raise AssertionError(plan)
    planned = perf_counter_ns()
    if executor == "bitmap":
        ids = bitmap_execute(masks, order)
        probes = None
    else:
        ids, probes = scalar_execute(masks, order)
    ended = perf_counter_ns()
    return ids, probes, order, {
        "acquisition_ns": acquired - start,
        "planning_ns": planned - acquired,
        "execution_and_materialization_ns": ended - planned,
        "total_ns": ended - start,
    }


@pytest.mark.parametrize("m", [3, 12])
def test_runtime_and_exact_candidate_invariance(m):
    frozen = acquire(m)
    assert len(frozen) == len(set(frozen)) == m
    expected = constructive_oracle()
    assert len(expected) == 100
    cached_order = exact(frozen)
    cert = audit_weighted_order(frozen, (1,) * m)
    assert cert["retained"] == 100
    # Exact and greedy planners operate on the same frozen masks and costs.
    # Cold paths include compilation; warm paths reuse the very same masks.
    cases = [
        (mode, plan, executor)
        for mode in ("cold", "warm")
        for plan, executor in (
            ("input", "scalar"), ("greedy", "scalar"), ("exact", "scalar"),
            ("count", "bitmap"), ("greedy", "bitmap"), ("exact", "bitmap"),
        )
    ] + [("warm", "cached_exact", "scalar"), ("warm", "cached_exact", "bitmap")]
    rows = {case: [] for case in cases}
    # One untimed-as-evidence warmup per path; rotate measured path ordering.
    for rep in range(-1, REPEATS):
        offset = max(rep, 0) % len(cases)
        for case in cases[offset:] + cases[:offset]:
            ids, probes, order, times = run_once(m, frozen, cached_order, *case)
            assert ids == expected
            assert sorted(order) == list(range(m))
            assert sum(times[k] for k in (
                "acquisition_ns", "planning_ns", "execution_and_materialization_ns"
            )) == times["total_ns"]
            if case[2] == "scalar":
                assert probes >= cert["optimal"]["scalar_probes"]
                if case[1] in ("exact", "cached_exact"):
                    assert probes == cert["optimal"]["scalar_probes"]
                if case[1] == "greedy":
                    assert probes == cert["baselines"]["greedy_exclusion_per_cost"]["scalar_probes"]
            if rep >= 0:
                rows[case].append({"order": list(order), "scalar_probes": probes, **times})

    raw = bytearray(WIDTH)
    for n in expected:
        raw[n >> 3] |= 1 << (n & 7)
    digest = sha256(raw).hexdigest()
    assert digest == cert["final_mask_sha256"]
    report = {
        "schema": "pl5-filter-runtime-v3747-1",
        "fixture": "INTERNAL/AI_AUTHORED",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "rules": m,
        "retained": len(expected),
        "final_mask_sha256": digest,
        "rule_mask_sha256": cert["rule_mask_sha256"],
        "logical_cache_payload_bytes": WIDTH * m,
        "exact_audit_subsets": cert["subsets"],
        "exact_audit_transitions_per_solve": cert["transitions_per_solve"],
        "samples_per_path": REPEATS,
        "historical_coverage_measured": False,
        "paths": [
            {
                "mode": case[0], "planner": case[1], "executor": case[2],
                "samples": rows[case],
                "median_total_ns": median(s["total_ns"] for s in rows[case]),
                "median_planning_ns": median(s["planning_ns"] for s in rows[case]),
            }
            for case in cases
        ],
    }
    print("V3747_RUNTIME_JSON=" + json.dumps(report, sort_keys=True))


# V3.7.48: isolated redundancy and cache-cost experiment.
# Frozen hypothesis: one suffix scan plus a conditional prefix scan produces
# an inclusion-minimal equivalent AND subset in O(m) bitmap operations.
# No assertion of globally fewest rules or wall-clock speedup.
# If removal of i enlarges the intersection at its visit, further removals
# cannot destroy that extra identity. Otherwise deletion preserves the target.
# The invariant is prefix AND unprocessed suffix == original intersection.


def direct_and(masks, full, order=None):
    active = full
    for i in range(len(masks)) if order is None else order:
        active &= masks[i]
        if not active:
            break
    return active


def prune_equivalent(masks, full):
    suffix = [full] * (len(masks) + 1)
    for i in range(len(masks) - 1, -1, -1):
        suffix[i] = masks[i] & suffix[i + 1]
    target = suffix[0]
    prefix = full
    kept = []
    for i, mask in enumerate(masks):
        if prefix & suffix[i + 1] != target:
            kept.append(i)
            prefix &= mask
    return tuple(kept), target


def test_v3748_exhaustive_set_oracle():
    from itertools import product
    domain = set(range(3))
    for n in range(4):
        for masks in product(range(8), repeat=n):
            subsets = [{j for j in domain if mask & (1 << j)}
                       for mask in masks]

            def oracle(indices):
                result = domain.copy()
                for i in indices:
                    result &= subsets[i]
                return result

            kept, target = prune_equivalent(masks, 7)
            expected = oracle(range(n))
            assert {j for j in domain if target & (1 << j)} == expected
            assert oracle(kept) == expected
            for i in kept:
                assert oracle(j for j in kept if j != i) > expected
    # Removing all individually redundant rules simultaneously is unsafe.
    assert prune_equivalent((3, 3), 7) == ((1,), 3)
    # Inclusion-minimal need not mean minimum cardinality.
    assert prune_equivalent((1, 3, 5), 7) == ((1, 2), 1)
    assert prune_equivalent((), 7) == ((), 7)
    assert prune_equivalent((0, 7), 7) == ((0,), 0)


@pytest.mark.parametrize("m", [3, 12])
def test_v3748_redundancy_and_cache_runtime(m):
    masks = acquire(m)
    expected_ids = constructive_oracle()
    raw = bytearray(WIDTH)
    for n in expected_ids:
        raw[n >> 3] |= 1 << (n & 7)
    expected = int.from_bytes(raw, "little")
    kept, target = prune_equivalent(masks, FULL)
    assert target == expected == direct_and(masks, FULL)
    assert len(kept) == 3
    assert all(direct_and(masks, FULL, tuple(j for j in kept if j != i))
               != expected for i in kept)
    # Equal inputs, exact tuple equality rather than digest-only cache keys.
    # A one-entry cache bounds storage; changed domain or masks replace it.
    def lookup(cache, full, rules):
        key = (full, rules)
        if cache and cache[0] == key:
            return cache[1]
        value = prune_equivalent(rules, full)
        cache[:] = [key, value]
        return value

    cache = []
    assert lookup(cache, FULL, masks) == (kept, target)
    # A changed previously retained identity must be excluded, even if
    # the edit is made to a mask that was previously redundant.
    idx = next((i for i in range(m) if i not in kept), 0)
    changed = list(masks)
    changed[idx] ^= 1 << expected_ids[0]
    changed = tuple(changed)
    changed_target = direct_and(changed, FULL)
    assert changed_target.bit_count() == 99
    assert lookup(cache, FULL, changed)[1] == changed_target
    assert lookup(cache, FULL, masks)[1] == target
    # An exact domain change must also invalidate the one-entry cache.
    smaller = FULL ^ (1 << expected_ids[0])
    assert lookup(cache, smaller, masks)[1] == direct_and(masks, smaller)
    assert lookup(cache, FULL, masks)[1] == target

    # Benchmark from already compiled, immutable bitmaps. All paths return
    # the same bitmap, not candidate materialization; acquisition is excluded
    # equally. Include cache construction and changed-input replacement.
    def direct():
        return direct_and(masks, FULL)

    def prune_cold():
        order, _ = prune_equivalent(masks, FULL)
        return direct_and(masks, FULL, order)

    def cached_order():
        order, _ = lookup(cache, FULL, masks)
        return direct_and(masks, FULL, order)

    def cached_final():
        return lookup(cache, FULL, masks)[1]

    def build_cache():
        local = []
        return lookup(local, FULL, masks)[1]

    def invalidate():
        # Prepare the opposite key outside the measured interval in caller.
        return lookup(cache, FULL, masks)[1]

    paths = [direct, prune_cold, cached_order, cached_final,
             build_cache, invalidate]
    rows = {fn.__name__: [] for fn in paths}
    for rep in range(-1, 15):
        offset = max(rep, 0) % len(paths)
        for fn in paths[offset:] + paths[:offset]:
            lookup(cache, FULL, changed if fn is invalidate else masks)
            start = perf_counter_ns()
            result = fn()
            elapsed = perf_counter_ns() - start
            assert result == expected
            if rep >= 0:
                rows[fn.__name__].append(elapsed)
    print("V3748_REDUNDANCY_JSON=" + json.dumps({
        "fixture": "INTERNAL/AI_AUTHORED",
        "platform": platform.platform(), "python": platform.python_version(),
        "rules": m, "kept_indices": list(kept), "retained": target.bit_count(),
        "final_mask_sha256": sha256(raw).hexdigest(),
        "historical_coverage_measured": False,
        "acquisition_and_materialization_excluded": True,
        "cache_key": "exact ordered immutable masks and full domain",
        "cache_entries": 1,
        "samples_ns": rows,
        "median_ns": {name: median(samples) for name, samples in rows.items()},
    }, sort_keys=True))
