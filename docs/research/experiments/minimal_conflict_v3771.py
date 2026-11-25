"""V3.7.71: exact minimal conflict-core audit of frozen signed filters.

INTERNAL/AI_AUTHORED. No historical records are read. No new filter masks.
A conflict core is an empty signed conjunction whose every one-literal
deletion is nonempty. Enumerate all 3**12 consistent signed states.
"""
from collections import Counter
from hashlib import sha256
import json
import unittest

from signed_order_v3763 import (
    freeze, partition, ternary_counts, literals, full_state, DOMAIN, CAP,
    digest, vector_digest,
)


def cores_and_closure(counts, powers):
    """Find minimal conflicts; then independently propagate their closure.

    width[s] is the minimum number of literals in any core contained in s;
    zero means no core. Removing a literal always decreases the state index.
    """
    cores = []
    for s in range(1, len(counts)):
        if counts[s] == 0 and all(counts[s-p] > 0
                                  for _, p in literals(s, powers)):
            cores.append(s)
    width = bytearray(len(counts))
    for s in cores:
        width[s] = len(tuple(literals(s, powers)))
    for s in range(1, len(counts)):
        for _, p in literals(s, powers):
            w = width[s-p]
            if w and (not width[s] or w < width[s]):
                width[s] = w
    assert all(bool(w) == (k == 0) for k, w in zip(counts, width))
    return cores, width


def direct(s, raw, size, powers):
    current = (1 << size)-1
    for j, p in literals(s, powers):
        current &= raw[j] if p == 2*powers[j] else ((1 << size)-1) ^ raw[j]
    return current


def witnesses(s, raw, size, powers):
    """Each single deletion has a concrete retained identity."""
    assert direct(s, raw, size, powers) == 0
    result = []
    for j, p in literals(s, powers):
        candidate = direct(s-p, raw, size, powers)
        assert candidate
        witness = (candidate & -candidate).bit_length()-1
        result.append({"rule_index": j, "required_truth": int(p == 2*powers[j]),
                       "deletion_witness": witness})
    return result


def audit():
    names, raw, _ = freeze()
    _, ks = partition(raw, DOMAIN)
    powers, counts = ternary_counts(ks, len(raw))
    assert len(raw) == 12 and len(counts) == 531441
    assert sum(0 < k <= CAP for k in ks) == 893
    cores, width = cores_and_closure(counts, powers)
    ledger = [{"state": s, "literals": witnesses(s, raw, DOMAIN, powers)}
              for s in cores]
    empty = sum(k == 0 for k in counts)
    by_core_size = Counter(len(row["literals"]) for row in ledger)
    by_min_width = Counter(w for w in width if w)
    # Equal universe and exact output semantics; count structural pruning
    # opportunities rather than claiming a runtime improvement.
    baselines = {str(limit): {
        "empty_states_detected": sum(v for w,v in by_min_width.items() if w <= limit),
        "empty_states_missed": sum(v for w,v in by_min_width.items() if w > limit),
        "core_inventory_size": sum(v for w,v in by_core_size.items() if w <= limit),
        "nonempty_states_rejected": 0,
    } for limit in (1,2,3,len(raw))}
    assert baselines[str(len(raw))]["empty_states_detected"] == empty
    return {
        "schema": "pl5-minimal-conflict-v3771-1", "source": "INTERNAL/AI_AUTHORED",
        "domain": DOMAIN, "cap": CAP, "rule_names": names,
        "rule_mask_sha256": [digest(m) for m in raw],
        "counts_sha256": vector_digest(counts),
        "state_count": len(counts), "empty_states": empty,
        "nonempty_states_at_cap": sum(0 < k <= CAP for k in counts),
        "cores_by_size": dict(sorted(by_core_size.items())),
        "empty_states_by_shortest_core": dict(sorted(by_min_width.items())),
        "bounded_core_baselines": baselines,
        "complete_core_ledger": ledger,
        "core_ledger_sha256": sha256(json.dumps(ledger,sort_keys=True,
            separators=(",",":")).encode()).hexdigest(),
        "closure_sha256": sha256(width).hexdigest(),
        "historical_coverage_measured": False,
        "wall_clock_performance_measured": False,
        "limitations": ["static 12-rule inventory only", "exponential offline enumeration",
                        "structural pruning counts, not measured execution savings",
                        "nonempty capped states are not selected by this method"],
    }


class Tests(unittest.TestCase):
    def test_three_way_conflict_missed_by_pairs(self):
        # Three pairwise compatible positive masks with empty triple intersection.
        raw = (0b011, 0b110, 0b101)
        _, ks = partition(raw, 3)
        powers, counts = ternary_counts(ks, len(raw))
        cores, width = cores_and_closure(counts, powers)
        target = full_state(7, powers)
        self.assertIn(target, cores)
        self.assertEqual(width[target], 3)
        self.assertEqual(len(witnesses(target, raw, 3, powers)), 3)

    def test_toy_exhaustive_independent_subset_oracle(self):
        for raw, size in (((0b10101010,0b11001100,0b10110001,0b10101010),8),
                          ((0,15,3,5),4), ((3,6,5),3)):
            _, ks = partition(raw, size)
            powers, counts = ternary_counts(ks, len(raw))
            cores, width = cores_and_closure(counts, powers)
            brute = [direct(s, raw, size, powers).bit_count() for s in range(len(counts))]
            self.assertEqual(list(counts), brute)
            for s, k in enumerate(brute):
                parts = [p for _,p in literals(s,powers)]
                subset_states = [0]
                for p in parts:
                    subset_states += [t+p for t in subset_states]
                empty_widths = [len(tuple(literals(t,powers))) for t in subset_states
                                if brute[t] == 0]
                self.assertEqual(width[s], min(empty_widths, default=0))
                self.assertEqual(s in cores, k == 0 and all(brute[s-p] for p in parts))
            for s in cores:
                witnesses(s, raw, size, powers)

    def test_frozen_inventory(self):
        r = audit()
        self.assertEqual(r["state_count"], 3**12)
        self.assertEqual(sum(r["empty_states_by_shortest_core"].values()), r["empty_states"])
        self.assertEqual(r["bounded_core_baselines"]["12"]["empty_states_missed"],0)
        self.__class__.result = r


if __name__ == "__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3771_CONFLICT_JSON="+json.dumps(Tests.result,sort_keys=True))
