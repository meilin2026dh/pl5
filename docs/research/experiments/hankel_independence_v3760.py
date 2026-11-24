"""V3.7.60: exact Hankel determinant sign filter, frozen static novelty.
INTERNAL/AI_AUTHORED. No historical records read or thresholds optimized.
"""
from collections import Counter
from hashlib import sha256
from itertools import permutations
import json
import unittest

from number_theory_independence_v3751 import (
    DOMAIN, existing_static_masks, signatures_and_groups, _partition,
)
from spectral_independence_v3754 import STATIC_MASK_MANIFEST_SHA256
from historical_operator_walkforward_v3756 import masks, RULE_NAMES


def determinant(n):
    if type(n) is not int or not 0 <= n < DOMAIN:
        raise ValueError("five-digit ID out of range")
    a,b,c,d,e = map(int, f"{n:05d}")
    return a*c*e + 2*b*c*d - a*d*d - b*b*e - c*c*c


PERMS = tuple((p, (-1)**sum(p[i] > p[j] for i in range(3)
                           for j in range(i+1,3)))
              for p in permutations(range(3)))


def oracle(n):
    digits = [(n//q)%10 for q in (10000,1000,100,10,1)]
    h = [[digits[i+j] for j in range(3)] for i in range(3)]
    return sum(sign*h[0][p[0]]*h[1][p[1]]*h[2][p[2]] for p,sign in PERMS)


def choose2(n):
    return n*(n-1)//2


def digest(mask):
    return sha256(mask.to_bytes(DOMAIN//8,"little")).hexdigest()


def audit():
    old = existing_static_masks()
    manifest = [{"name":name,"sha256":digest(mask)} for name,mask in old]
    if sha256(json.dumps(manifest,sort_keys=True,separators=(",",":")).encode()).hexdigest() != STATIC_MASK_MANIFEST_SHA256:
        raise AssertionError("legacy static mask drift")
    new = list(zip(RULE_NAMES,masks(),strict=True))
    baseline = old+new
    assert len(baseline)==68
    groups = signatures_and_groups(baseline)
    values = [determinant(n) for n in range(DOMAIN)]
    for n,v in enumerate(values):
        if v!=oracle(n) or v!=values[int(f"{n:05d}"[::-1])]:
            raise AssertionError("determinant oracle or reversal invariant mismatch")
    binary = [int(v>0) for v in values]
    packed = bytearray(DOMAIN//8)
    for n,b in enumerate(binary):
        if b:
            packed[n>>3] |= 1<<(n&7)
    bitmap = int.from_bytes(packed,"little")
    assert bitmap.bit_count()==sum(binary)
    # Two independent pair calculations: group histogram and cross-product
    # of true and false counts within each prior signature.
    row = _partition(groups,binary)
    extra = sum(sum(binary[n] for n in g) *
                (len(g)-sum(binary[n] for n in g)) for g in groups.values())
    assert row["newly_distinguished_pairs"]==extra
    assert row["old_indistinguishable_pairs"]==sum(choose2(len(g)) for g in groups.values())
    witness = row["witness_ids"]
    if witness is not None:
        a,b = witness
        assert all(((m>>a)&1)==((m>>b)&1) for _,m in baseline)
        assert (oracle(a)>0)!=(oracle(b)>0)
    else:
        assert extra==0
    refined = Counter((key,binary[n]) for key,g in groups.items() for n in g)
    assert sum(refined.values())==DOMAIN
    assert len(refined)==len(groups)+row["split_old_classes"]
    assert sum(choose2(k) for k in refined.values())+extra==row["old_indistinguishable_pairs"]
    signs=Counter((v>0)-(v<0) for v in values)
    # Domain-only compression and marginal split in already frozen ten-rule
    # atoms. These are not selected filters.
    atoms=signatures_and_groups(new)
    before_small=sum(len(g) for g in atoms.values() if len(g)<=100)
    after_counts=Counter((key,binary[n]) for key,g in atoms.items() for n in g)
    after_small=sum(k for k in after_counts.values() if k<=100)
    assert before_small<=after_small
    return {
      "schema":"pl5-hankel-determinant-v3760-1",
      "source":"INTERNAL/AI_AUTHORED",
      "domain":DOMAIN,"rule":"det_H_gt_0",
      "baseline_count":len(baseline),
      "baseline_manifest":manifest+[{"name":name,"sha256":digest(m)} for name,m in new],
      "standalone_k":sum(binary),"standalone_sha256":digest(bitmap),
      "sign_counts":dict(sorted(signs.items())),
      "distinct_integer_determinants":len(set(values)),
      "old_classes":len(groups),"new_classes":len(refined),
      "static_independence":row,
      "remaining_indistinguishable_pairs":sum(choose2(k) for k in refined.values()),
      "ten_rule_atom_count":len(atoms),"eleven_rule_atom_count":len(after_counts),
      "ten_rule_small_atom_union_k":before_small,
      "eleven_rule_small_atom_union_k":after_small,
      "historical_coverage_measured":False,
      "small_atom_union_is_not_one_capped_filter":True,
      "practical_filter_value_proven":False,
    }


class Tests(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(determinant(0),0)
        self.assertEqual(determinant(10101),0)
        self.assertEqual(determinant(10001),0)
        self.assertEqual(determinant(11111),0)
        self.assertEqual(determinant(100),-1)
        self.assertEqual(determinant(10201),-6)
        for n in (-1,DOMAIN,True):
            with self.assertRaises(ValueError):
                determinant(n)

    def test_small_partition(self):
        groups={"a":[0,1,2],"b":[3,4]}
        self.assertEqual(_partition(groups,[0,1,1,0,1])["newly_distinguished_pairs"],3)

    def test_exact_domain(self):
        r=audit()
        self.assertEqual(r["baseline_count"],68)
        self.assertEqual(sum(r["sign_counts"].values()),DOMAIN)
        self.assertEqual(r["sign_counts"][1],r["standalone_k"])
        self.assertEqual(r["ten_rule_atom_count"],319)
        self.assertEqual(r["ten_rule_small_atom_union_k"],5082)
        self.assertEqual(r["static_independence"]["boolean_novelty_proven"],
                         r["static_independence"]["witness_ids"] is not None)

if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3760_HANKEL_JSON="+json.dumps(audit(),sort_keys=True))
