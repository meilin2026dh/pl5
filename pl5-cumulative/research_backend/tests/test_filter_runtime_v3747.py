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
