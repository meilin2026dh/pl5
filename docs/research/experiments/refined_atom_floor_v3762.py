"""V3.7.62: exact refinement audit of the two previously frozen filters.
INTERNAL/AI_AUTHORED. The previously exposed historical panel is diagnostic only.
"""
from collections import Counter
from hashlib import sha256
import json
import unittest

from historical_operator_walkforward_v3756 import (
    DOMAIN, WARMUP, TEST_WINDOWS, RULE_NAMES, masks, verified_rows,
    history_digest, random_control,
)
from hankel_independence_v3760 import determinant
from polynomial_squarefactor_v3761 import repeated_factor, packed_mask
from number_theory_independence_v3751 import signatures_and_groups

CAP = 100
FULL = (1 << DOMAIN) - 1


def digest(mask):
    return sha256(mask.to_bytes(DOMAIN//8, "little")).hexdigest()


def partition(raw, size):
    """All signed atoms, independently verified by direct truth signatures."""
    full = (1 << size) - 1
    atoms = [full]
    for m in raw:
        # Index bit j is the truth value of predicate j.
        atoms = [a & (full ^ m) for a in atoms] + [a & m for a in atoms]
    seen = 0
    for atom in atoms:
        assert not (seen & atom)
        seen |= atom
    assert seen == full
    counts = [a.bit_count() for a in atoms]
    assert sum(counts) == size
    return atoms, counts


def freeze():
    raw = tuple(masks())
    assert len(raw) == 10
    h = packed_mask(determinant(n) > 0 for n in range(DOMAIN))
    p = packed_mask(repeated_factor(tuple(map(int, f"{n:05d}"))) for n in range(DOMAIN))
    assert h.bit_count() == 15053 and p.bit_count() == 34488
    raw += (h,p)
    names = RULE_NAMES + ("det_H_gt_0", "F3_squarefactor")
    groups = signatures_and_groups(list(zip(names, raw)))
    oracle = Counter({int.from_bytes(key,"little"):len(v) for key,v in groups.items()})
    atoms12, counts12 = partition(raw, DOMAIN)
    assert all(counts12[s] == oracle[s] for s in range(1<<12))
    stages = {}
    for n, expected in ((10,5082),(11,9230),(12,16244)):
        atoms, counts = partition(raw[:n], DOMAIN)
        folded = Counter()
        for s, count in oracle.items():
            folded[s & ((1<<n)-1)] += count
        assert all(counts[s] == folded[s] for s in range(1<<n))
        support = 0
        for a,k in zip(atoms,counts):
            if 0 < k <= CAP:
                support |= a
        assert support.bit_count() == expected
        stages[n] = (counts,support)
    assert stages[10][1] & stages[11][1] == stages[10][1]
    assert stages[11][1] & stages[12][1] == stages[11][1]
    return names,raw,stages


def audit():
    names,raw,stages = freeze()
    # All masks, support unions and the three comparison stages are fixed
    # before the previously exposed panel is opened. No fitting or selection.
    report = {
        str(n): {
            "nonempty_atoms":sum(k>0 for k in counts),
            "nonempty_atoms_at_cap":sum(0<k<=CAP for k in counts),
            "diagnostic_union_k":support.bit_count(),
            "diagnostic_union_sha256":digest(support),
            "retrospective_union_retained":0,
            "matched_k_control_retained":0,
            "matched_k_reference_numerator":TEST_WINDOWS*support.bit_count(),
            "matched_k_reference_denominator":DOMAIN,
            "minimum_observed_atom_k":None,
            "maximum_observed_atom_k":None,
        } for n,(counts,support) in stages.items()
    }
    rows = verified_rows()
    assert len(rows)-WARMUP == TEST_WINDOWS
    ledger=[]
    for idx in range(WARMUP,len(rows)):
        issue = rows[idx][0]
        prefix = history_digest(rows[:idx])
        # Matched-size controls use only earlier rows, fixed stage and issue.
        controls = {n:random_control(prefix,issue,"v3762_atom_union_"+str(n),
                    support.bit_count()) for n,(_,support) in stages.items()}
        target = int(rows[idx][1])
        signature = sum(((m>>target)&1)<<j for j,m in enumerate(raw))
        floors = []
        matched = []
        for n,(counts,support) in stages.items():
            k = counts[signature & ((1<<n)-1)]
            assert k > 0
            assert bool((support>>target)&1) == (k<=CAP)
            floors.append(k)
            row = report[str(n)]
            row["retrospective_union_retained"] += int(k<=CAP)
            hit = int(target in controls[n])
            row["matched_k_control_retained"] += hit
            matched.append(hit)
            mn = row["minimum_observed_atom_k"]
            mx = row["maximum_observed_atom_k"]
            row["minimum_observed_atom_k"] = k if mn is None else min(mn,k)
            row["maximum_observed_atom_k"] = k if mx is None else max(mx,k)
        assert floors[0]>=floors[1]>=floors[2]
        ledger.append({"issue":issue,"prefix_sha256":prefix,
                       "atom_k_10_11_12":floors,"matched_control_retained":matched})
    for row in report.values():
        row["retrospective_union_removed"] = TEST_WINDOWS-row["retrospective_union_retained"]
    return {
        "schema":"pl5-refined-atom-floor-v3762-1",
        "source":"INTERNAL/AI_AUTHORED",
        "domain":DOMAIN,"cap":CAP,"windows":TEST_WINDOWS,
        "rule_manifest":[{"name":name,"sha256":digest(m)} for name,m in zip(names,raw)],
        "stages":report,"ledger":ledger,
        "historical_source":"RETROSPECTIVE_CROSSCHECKED_TRANSCRIPTS_NOT_SOURCE_AUTHENTICATED",
        "previously_exposed_development_panel":True,
        "historical_target_used_to_construct_masks":False,
        "diagnostic_union_is_not_one_capped_filter":True,
        "per_record_atom_floor_is_not_selection_policy":True,
        "independent_historical_validation_established":False,
    }


class Tests(unittest.TestCase):
    def test_toy_full_boolean_partition(self):
        raw = (0b10101010,0b11001100,0b11110000)
        atoms,counts=partition(raw,8)
        self.assertEqual(counts,[1]*8)
        for s,atom in enumerate(atoms):
            self.assertEqual(atom,1<<s)
        # A duplicate rule cannot further split any existing atom.
        _,dup=partition(raw+(raw[0],),8)
        self.assertEqual(sorted(k for k in dup if k),[1]*8)

    def test_full_domain_and_fixed_history(self):
        r=audit()
        self.assertEqual(r["windows"],20)
        self.assertEqual(r["stages"]["10"]["retrospective_union_retained"],0)
        self.assertEqual([r["stages"][str(n)]["diagnostic_union_k"]
                          for n in (10,11,12)],[5082,9230,16244])
        for row in r["stages"].values():
            self.assertEqual(row["retrospective_union_retained"]+
                             row["retrospective_union_removed"],20)
        for entry in r["ledger"]:
            a,b,c=entry["atom_k_10_11_12"]
            self.assertGreaterEqual(a,b)
            self.assertGreaterEqual(b,c)

    def test_replay(self):
        self.assertEqual(audit(),audit())

if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3762_REFINEMENT_JSON="+json.dumps(audit(),sort_keys=True))
