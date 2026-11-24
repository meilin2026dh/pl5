"""V3.7.64 exact equivalent-filter minimization, INTERNAL/AI_AUTHORED.

For each capped full atom, minimize literals and weighted checking cost
over all equivalent signed sub-conjunctions. No historical records used.
"""
import json
import unittest
from hashlib import sha256
from itertools import permutations

from signed_order_v3763 import (
    freeze, partition, ternary_counts, bellman, full_state, literals,
    optimal_order, bitmap_replay, DOMAIN, CAP, digest,
)


def subset_states(signature, powers):
    states = [0]
    for j, p in enumerate(powers):
        part = (1 + ((signature >> j) & 1)) * p
        states += [s + part for s in states]
    return states


def solutions(signature, powers, counts, work):
    states = subset_states(signature, powers)
    full = states[-1]
    k = counts[full]
    if not k:
        raise ValueError("nonempty atoms only")
    # Each subset contains the full atom. Equal cardinality proves equality.
    eligible = [(mask.bit_count(), s) for mask, s in enumerate(states)
                if counts[s] == k]
    shortest = min(eligible, key=lambda t: (t[0], work[t[1]], t[1]))
    cheapest = min(eligible, key=lambda t: (work[t[1]], t[0], t[1]))
    # Single-pass reverse deletion, no global search; all removed literals
    # preserve the exact set. A failed removal cannot become feasible later.
    greedy = full
    for _, part in reversed(tuple(literals(full, powers))):
        if counts[greedy-part] == k:
            greedy -= part
    return shortest, cheapest, greedy, len(eligible)


def check_state(s, full_bitmap, raw, powers, weights, work, size):
    order = optimal_order(s, work[1], powers)
    cost, bitmap = bitmap_replay(order, raw, powers, size, weights)
    if bitmap != full_bitmap or cost != work[0][s]:
        raise AssertionError("membership or independent cost mismatch")
    return cost


def audit():
    names, raw, _ = freeze()
    n = len(raw)
    atoms, ks = partition(raw, DOMAIN)
    powers, counts = ternary_counts(ks, n)
    models = {"unit": (1,)*n,
              "heterogeneous_abstract": (1,1,1,1,1,1,4,4,4,5,3,8)}
    result = {}
    for label, weights in models.items():
        w = bellman(counts, powers, weights)
        rows = []
        for sig, k in enumerate(ks):
            if not 0 < k <= CAP:
                continue
            full = full_state(sig, powers)
            short, cheap, greedy, equivalent_count = solutions(sig, powers, counts, w[0])
            g_n = len(tuple(literals(greedy, powers)))
            full_cost = check_state(full, atoms[sig], raw, powers, weights, w, DOMAIN)
            short_cost = check_state(short[1], atoms[sig], raw, powers, weights, w, DOMAIN)
            cheap_cost = check_state(cheap[1], atoms[sig], raw, powers, weights, w, DOMAIN)
            greedy_cost = check_state(greedy, atoms[sig], raw, powers, weights, w, DOMAIN)
            assert short[0] <= g_n <= n
            assert cheap_cost <= min(full_cost, short_cost, greedy_cost)
            rows.append({"signature":sig, "k":k, "equivalent_subset_count":equivalent_count,
                         "minimum_literals":short[0], "minimum_literal_state":short[1],
                         "minimum_cost_literals":cheap[0], "minimum_cost_state":cheap[1],
                         "greedy_literals":g_n, "greedy_state":greedy,
                         "full_optimal_cost":full_cost, "shortest_cost":short_cost,
                         "minimum_cost":cheap_cost, "greedy_cost":greedy_cost})
        assert len(rows)==893
        result[label] = {
            "weights":weights, "atom_count":len(rows),
            "full_literal_count":len(rows)*n,
            "minimum_literal_count":sum(r["minimum_literals"] for r in rows),
            "minimum_cost_literal_count":sum(r["minimum_cost_literals"] for r in rows),
            "greedy_literal_count":sum(r["greedy_literals"] for r in rows),
            "atoms_with_removable_literals":sum(r["minimum_literals"]<n for r in rows),
            "greedy_not_shortest":sum(r["greedy_literals"]>r["minimum_literals"] for r in rows),
            "greedy_not_cheapest":sum(r["greedy_cost"]>r["minimum_cost"] for r in rows),
            "cost_totals":{key:sum(r[key] for r in rows) for key in
                ("full_optimal_cost","shortest_cost","minimum_cost","greedy_cost")},
            "worst_greedy_regret":max(r["greedy_cost"]-r["minimum_cost"] for r in rows),
            "ledger_sha256":sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        }
    return {"schema":"pl5-equivalent-rule-minimization-v3764-1",
            "source":"INTERNAL/AI_AUTHORED","domain":DOMAIN,"cap":CAP,
            "rule_names":names,"rule_mask_sha256":[digest(m) for m in raw],
            "all_subsets_per_atom":2**n,"models":result,
            "candidate_membership_preserved":True,
            "historical_coverage_measured":False,
            "wall_clock_performance_measured":False,
            "planning_cost_excluded":True}


class Tests(unittest.TestCase):
    def test_exhaustive_toy_oracle(self):
        raw = (0b10101010,0b11001100,0b10110001,0b10101010)
        size=8
        atoms, ks = partition(raw,size)
        powers, counts = ternary_counts(ks,len(raw))
        weights=(1,3,2,7)
        w,last=bellman(counts,powers,weights)
        for sig,k in enumerate(ks):
            if not k:
                continue
            short,cheap,greedy,equivalent_count=solutions(sig,powers,counts,w)
            full=full_state(sig,powers)
            full_literals=tuple(literals(full,powers))
            oracle=[]
            for mask in range(1<<len(raw)):
                chosen=tuple(x for i,x in enumerate(full_literals) if mask>>i&1)
                costs=[]
                for order in permutations(chosen):
                    cost,bitmap=bitmap_replay(order,raw,powers,size,weights)
                    if bitmap==atoms[sig]:
                        costs.append(cost)
                if costs:
                    oracle.append((len(chosen), min(costs)))
            self.assertEqual(equivalent_count,len(oracle))
            self.assertEqual((short[0],w[short[1]]),min(oracle))
            self.assertEqual((w[cheap[1]],cheap[0]),min((c,n) for n,c in oracle))
            check_state(greedy,atoms[sig],raw,powers,weights,(w,last),size)

    def test_empty_rejected(self):
        p,c=ternary_counts([0,2],1)
        w,_=bellman(c,p,(1,))
        with self.assertRaises(ValueError):
            solutions(0,p,c,w)

    def test_full_domain(self):
        r=audit()
        for m in r["models"].values():
            self.assertEqual(m["atom_count"],893)
            self.assertLessEqual(m["minimum_literal_count"],m["greedy_literal_count"])
            self.assertLessEqual(m["cost_totals"]["minimum_cost"],m["cost_totals"]["full_optimal_cost"])
        self.__class__.result=r


if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3764_MINIMIZATION_JSON="+json.dumps(Tests.result,sort_keys=True))
