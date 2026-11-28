"""V3.7.66 static signed-filter bitmap execution benchmark.
INTERNAL/AI_AUTHORED. No historical records accessed. All 893 capped
truth-signature queries from the frozen inventory are a fixed workload,
not a query-selection procedure. Timings are observations, not CI gates.
"""
import json
import platform
import statistics
from hashlib import sha256
from time import perf_counter_ns

from signed_order_v3763 import (
    freeze, partition, ternary_counts, bellman, full_state, literals,
    greedy_order, optimal_order, DOMAIN, CAP, digest,
)
from equivalent_rule_minimization_v3764 import solutions

REPEATS = 7
WEIGHTS = (1, 1, 1, 1, 1, 1, 4, 4, 4, 5, 3, 8)
STRATEGIES = ("fixed", "adaptive_online", "adaptive_cached",
              "optimal_cached", "minimized_cached", "atom_lookup")


def setup(strategy, raw, size, queries, weights):
    full = (1 << size) - 1
    pairs = tuple((full ^ m, m) for m in raw)
    n = len(raw)
    powers = tuple(3**j for j in range(n))

    def apply(order):
        current = full
        for j, part in order:
            current &= pairs[j][int(part == 2*powers[j])]
        return current

    if strategy == "fixed":
        return lambda sig: apply(literals(full_state(sig, powers), powers))
    atoms, ks = partition(raw, size)
    if strategy == "atom_lookup":
        return lambda sig: atoms[sig]
    powers, counts = ternary_counts(ks, n)
    if strategy == "adaptive_online":
        return lambda sig: apply(greedy_order(full_state(sig, powers),
                                            counts, powers, weights, True))
    if strategy == "adaptive_cached":
        plans = {sig: greedy_order(full_state(sig, powers), counts,
                                  powers, weights, True) for sig in queries}
    elif strategy in ("optimal_cached", "minimized_cached"):
        work, last = bellman(counts, powers, weights)
        plans = {}
        for sig in queries:
            state = full_state(sig, powers)
            if strategy == "minimized_cached":
                _, cheap, _, _ = solutions(sig, powers, counts, work)
                state = cheap[1]
            plans[sig] = optimal_order(state, last, powers)
    else:
        raise ValueError(strategy)
    return lambda sig: apply(plans[sig])


def check_toy():
    raw = (0b10101010, 0b11001100, 0b10110001, 0b10101010)
    atoms, _ = partition(raw, 8)
    queries = tuple(range(16))
    for strategy in STRATEGIES:
        # The exact minimizer accepts nonempty atoms only.
        q = tuple(i for i in queries if atoms[i]) if strategy == "minimized_cached" else queries
        run = setup(strategy, raw, 8, q, (1, 3, 2, 7))
        assert all(run(i) == atoms[i] for i in q)


def bench():
    check_toy()
    t = perf_counter_ns()
    names, raw, _ = freeze()
    freeze_ns = perf_counter_ns() - t
    assert len(raw) == len(WEIGHTS) == 12
    # Separate untimed reference/workload construction; each strategy must
    # independently construct its own execution cache or planning tables.
    atoms, counts = partition(raw, DOMAIN)
    queries = tuple(i for i, k in enumerate(counts) if 0 < k <= CAP)
    assert len(queries) == 893
    expected = tuple(atoms[i] for i in queries)
    # Independent direct intersection for every fixed query.
    full = (1 << DOMAIN) - 1
    for sig, target in zip(queries, expected):
        candidate = full
        for j, m in enumerate(raw):
            candidate &= m if (sig >> j) & 1 else full ^ m
        assert candidate == target
    result = {}
    runners = {}
    # Measure setup once, then warm batches interleaved in rotating order.
    # Setup includes strategy-specific partition, complement, count and
    # planning construction. Shared frozen-mask generation is separate.
    for strategy in STRATEGIES:
        t = perf_counter_ns()
        run = setup(strategy, raw, DOMAIN, queries, WEIGHTS)
        setup_ns = perf_counter_ns() - t
        assert tuple(run(i) for i in queries) == expected
        runners[strategy] = run
        result[strategy] = {"setup_ns": setup_ns, "warm_batch_ns": []}
    for repeat in range(REPEATS):
        order = STRATEGIES[repeat % len(STRATEGIES):] + STRATEGIES[:repeat % len(STRATEGIES)]
        for strategy in order:
            run = runners[strategy]
            t = perf_counter_ns()
            actual = tuple(run(i) for i in queries)
            elapsed = perf_counter_ns() - t
            assert actual == expected
            result[strategy]["warm_batch_ns"].append(elapsed)
    for row in result.values():
        samples = row["warm_batch_ns"]
        med = int(statistics.median(samples))
        row["median_warm_batch_ns"] = med
        row["estimated_setup_plus_batches_ns"] = {
            str(b): row["setup_ns"] + b*med for b in (1, 10, 100)
        }
    # Stable evidence excludes clock values and machine metadata.
    ledger = sha256()
    for sig, mask in zip(queries, expected):
        ledger.update(sig.to_bytes(2, "little"))
        ledger.update(bytes.fromhex(digest(mask)))
    return {"schema": "pl5-bitmap-performance-v3766-1",
            "source": "INTERNAL/AI_AUTHORED",
            "platform": platform.platform(), "python": platform.python_version(),
            "domain": DOMAIN, "cap": CAP, "query_count": len(queries),
            "rule_names": names, "rule_mask_sha256": [digest(m) for m in raw],
            "candidate_ledger_sha256": ledger.hexdigest(),
            "candidate_membership_preserved": True,
            "historical_coverage_measured": False,
            "weights_abstract_not_measured": WEIGHTS,
            "shared_freeze_ns": freeze_ns, "warm_repeats": REPEATS,
            "setup_repeats": 1, "strategies": result,
            "scope": "cached bitmaps, full signed queries only",
            "limitations": ["warmup excluded from timings",
                            "setup plus batches is an estimate, not a measured cold run",
                            "all caches coexist; memory not benchmarked",
                            "no cross-machine speed ranking or timing gate"]}


if __name__ == "__main__":
    print("V3766_PERFORMANCE_JSON="+json.dumps(bench(), sort_keys=True))
