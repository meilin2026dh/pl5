"""V3.7.63: exact weighted short-circuit order for signed conjunctions.

INTERNAL/AI_AUTHORED. Extends the positive-only unit-check Bellman recurrence
of V3.7.31 to all ternary partial assignments of the 12 frozen V3.7.62 rules.
No historical data are opened, no filter masks are fitted or selected.
"""
from array import array
from fractions import Fraction
from hashlib import sha256
from itertools import permutations
import json
import struct
import unittest

from refined_atom_floor_v3762 import freeze, partition, DOMAIN, CAP, digest


def literals(state, powers):
    """Yield (rule index, signed contribution); trit 1=false, 2=true."""
    for j, p in enumerate(powers):
        trit = state % 3
        if trit:
            yield j, trit * p
        state //= 3


def full_state(signature, powers):
    return sum((1 + ((signature >> j) & 1)) * p
               for j, p in enumerate(powers))


def ternary_counts(atom_counts, n):
    if not 1 <= n <= 12 or len(atom_counts) != 1 << n:
        raise ValueError("bounded inventory and complete atom counts required")
    if any(k < 0 for k in atom_counts) or sum(atom_counts) > 100_000:
        raise ValueError("invalid counts")
    powers = tuple(3**j for j in range(n))
    counts = array("I", [0]) * (3**n)
    for signature, count in enumerate(atom_counts):
        counts[full_state(signature, powers)] = count
    # Both children of a wildcard state have larger indices. Each wildcard
    # splits disjointly into a false and a true restriction.
    for state in range(len(counts)-1, -1, -1):
        for p in powers:
            if (state // p) % 3 == 0:
                counts[state] = counts[state+p] + counts[state+2*p]
                break
    assert counts[0] == sum(atom_counts)
    return powers, counts


def bellman(counts, powers, weights):
    if len(weights) != len(powers) or any(type(w) is not int or w <= 0 for w in weights):
        raise ValueError("positive integer weights required")
    if len(counts) != 3**len(powers) or counts[0]*sum(weights) >= 2**32:
        raise ValueError("state inventory or weight budget invalid")
    work = array("I", [0]) * len(counts)
    last = bytearray(len(counts))
    # A last literal's cost is charged to every surviving prefix identity.
    # Every predecessor is smaller than its state, so this is acyclic.
    for state in range(1, len(counts)):
        best = None
        for j, part in literals(state, powers):
            prefix = state-part
            value = work[prefix] + weights[j]*counts[prefix]
            if best is None or value < best:
                best = value
                last[state] = j
        work[state] = best
    return work, last


def optimal_order(state, last, powers):
    rev = []
    while state:
        j = last[state]
        part = ((state//powers[j]) % 3)*powers[j]
        assert part
        rev.append((j, part))
        state -= part
    return tuple(reversed(rev))


def order_cost(order, counts, weights):
    prefix = 0
    total = 0
    for j, part in order:
        total += weights[j]*counts[prefix]
        prefix += part
    return total


def greedy_order(state, counts, powers, weights, adaptive):
    todo = list(literals(state, powers))
    order = []
    prefix = 0
    while todo:
        base = prefix if adaptive else 0
        # Maximum marginal removals per unit abstract cost; exact ratios.
        choice = max(todo, key=lambda item: (
            Fraction(counts[base]-counts[base+item[1]],weights[item[0]]),
            -item[0]))
        todo.remove(choice)
        order.append(choice)
        prefix += choice[1]
    return tuple(order)


def bitmap_replay(order, raw, powers, size, weights):
    full = (1 << size)-1
    current = full
    cost = 0
    for j, part in order:
        cost += current.bit_count()*weights[j]
        current &= raw[j] if part == 2*powers[j] else full ^ raw[j]
    return cost, current


def vector_digest(values):
    # Explicit little endian encoding, independent of native array byte order.
    return sha256(struct.pack("<%dI" % len(values), *values)).hexdigest()


def audit():
    names, raw, _ = freeze()
    n = len(raw)
    atoms, atom_counts = partition(raw, DOMAIN)
    powers, counts = ternary_counts(atom_counts, n)
    # Cross-check every ordinary positive-only state against direct masks,
    # and all full signed states against exact V3.7.62 Boolean atom counts.
    positive = [((1 << DOMAIN)-1, 0)] * (1 << n)
    for s in range(1, 1 << n):
        low = s & -s
        j = low.bit_length()-1
        parent, parent_state = positive[s ^ low]
        m, state = parent & raw[j], parent_state+2*powers[j]
        assert counts[state] == m.bit_count()
        positive[s] = m, state
    for s, k in enumerate(atom_counts):
        assert counts[full_state(s, powers)] == k
    assert len(counts) == 531441
    assert sum(0 < k <= CAP for k in atom_counts) == 893

    # These are abstract fixed sensitivity scenarios, NOT measured timings.
    models = {
        "unit": (1,)*n,
        "heterogeneous_abstract": (1,1,1,1,1,1,4,4,4,5,3,8),
    }
    reports = {}
    for label, weights in models.items():
        work, last = bellman(counts, powers, weights)
        rows = []
        for signature, k in enumerate(atom_counts):
            if not 0 < k <= CAP:
                continue
            state = full_state(signature, powers)
            orders = {
                "optimal": optimal_order(state,last,powers),
                "fixed": tuple(literals(state,powers)),
                "static_greedy": greedy_order(state,counts,powers,weights,False),
                "adaptive_greedy": greedy_order(state,counts,powers,weights,True),
            }
            row = {"signature":signature,"k":k}
            for strategy, order in orders.items():
                value = order_cost(order,counts,weights)
                independent_cost, final = bitmap_replay(order,raw,powers,DOMAIN,weights)
                assert independent_cost == value and final == atoms[signature]
                assert value >= work[state]
                row[strategy] = value
            assert row["optimal"] == work[state]
            rows.append(row)

        strategies = {}
        for key in ("fixed","static_greedy","adaptive_greedy"):
            worst = max(rows,key=lambda row:(row[key]-row["optimal"],-row["signature"]))
            strategies[key] = {
                "total_cost":sum(r[key] for r in rows),
                "strictly_suboptimal":sum(r[key] > r["optimal"] for r in rows),
                "max_absolute_regret":worst[key]-worst["optimal"],
                "worst_example":worst,
            }
        reports[label] = {
            "weights":weights,
            "optimal_cost_sum":sum(r["optimal"] for r in rows),
            "strategies":strategies,
            "all_state_optimum_sha256":vector_digest(work),
            "capped_atom_ledger_sha256":sha256(json.dumps(rows,sort_keys=True,
                separators=(",",":")).encode()).hexdigest(),
        }
    return {
        "schema":"pl5-signed-order-v3763-1",
        "source":"INTERNAL/AI_AUTHORED",
        "domain":DOMAIN,"cap":CAP,"rule_names":names,
        "rule_mask_sha256":[digest(m) for m in raw],
        "ternary_state_count":len(counts),
        "nonempty_signed_conjunctions_including_empty_rule_set":sum(k>0 for k in counts),
        "nonempty_signed_conjunctions_at_cap":sum(0<k<=CAP for k in counts),
        "nonempty_complete_atoms_at_cap":893,
        "counts_sha256":vector_digest(counts),
        "models":reports,
        "candidate_membership_preserved":True,
        "historical_coverage_measured":False,
        "wall_clock_performance_measured":False,
        "offline_planning_cost_excluded_from_execution_proxy":True,
    }


class Tests(unittest.TestCase):
    def test_all_toy_signed_states_against_independent_permutations(self):
        raw=(0b10101010,0b11001100,0b10110001,0b10101010)
        atoms, ks = partition(raw,8)
        powers, counts = ternary_counts(ks,len(raw))
        weights=(1,3,2,7)
        work,last=bellman(counts,powers,weights)
        for state in range(len(counts)):
            selected=tuple(literals(state,powers))
            brute=[]
            for order in permutations(selected):
                cost,final=bitmap_replay(order,raw,powers,8,weights)
                self.assertEqual(final.bit_count(),counts[state])
                brute.append(cost)
            self.assertEqual(work[state],min(brute))
            self.assertEqual(order_cost(optimal_order(state,last,powers),
                                        counts,weights),min(brute))
            for adaptive in (False,True):
                self.assertGreaterEqual(order_cost(greedy_order(state,counts,powers,
                    weights,adaptive),counts,weights),min(brute))

    def test_invalid_bound_and_cost(self):
        with self.assertRaises(ValueError):
            ternary_counts([1]*8192,13)
        powers,counts=ternary_counts([1,1],1)
        for bad in ((0,),(-1,),(1.5,),()):
            with self.assertRaises(ValueError):
                bellman(counts,powers,bad)

    def test_full_domain_and_replay(self):
        r=audit()
        self.assertEqual(r["ternary_state_count"],3**12)
        self.assertEqual(r["nonempty_complete_atoms_at_cap"],893)
        for model in r["models"].values():
            for strategy in model["strategies"].values():
                self.assertGreaterEqual(strategy["total_cost"],model["optimal_cost_sum"])
        # Bytewise deterministic evidence is independently checked in both CI platforms.
        self.__class__.result = r


if __name__ == "__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3763_ORDER_JSON="+json.dumps(Tests.result,sort_keys=True))
