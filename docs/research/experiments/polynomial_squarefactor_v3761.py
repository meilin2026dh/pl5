"""V3.7.61 — one frozen finite-field square-factor filter.
INTERNAL/AI_AUTHORED; static domain only; no historical data read.
"""
from collections import Counter
from itertools import product
from hashlib import sha256
import json
import unittest

from number_theory_independence_v3751 import (
    DOMAIN, existing_static_masks, signatures_and_groups, _partition,
)
from spectral_independence_v3754 import STATIC_MASK_MANIFEST_SHA256
from historical_operator_walkforward_v3756 import RULE_NAMES, masks
from hankel_independence_v3760 import determinant, digest

P = 3


def trim(poly):
    a = [v % P for v in poly]
    while a and a[-1] == 0:
        a.pop()
    return a


def remainder(a, b):
    a, b = trim(a), trim(b)
    if not b:
        raise ValueError("zero divisor")
    inv = pow(b[-1], -1, P)
    while a and len(a) >= len(b):
        offset = len(a) - len(b)
        c = a[-1] * inv % P
        for i, v in enumerate(b):
            a[offset+i] = (a[offset+i] - c*v) % P
        a = trim(a)
    return a


def repeated_factor(coefficients):
    # Nonzero nonconstant polynomials with gcd(f,f') of positive degree.
    # The zero polynomial is explicitly outside this rule.
    a = trim(coefficients)
    if len(a) < 2:
        return False
    b = trim([i*a[i] for i in range(1,len(a))])
    while b:
        a,b = b,remainder(a,b)
    return len(a) >= 2


def multiply(a,b):
    out = [0]*(len(a)+len(b)-1)
    for i,x in enumerate(a):
        for j,y in enumerate(b):
            out[i+j] = (out[i+j]+x*y)%P
    return out


def square_multiple_oracle():
    # Independent construction, no polynomial division or derivative.
    # A repeated irreducible factor of a nonzero polynomial of degree <=4
    # has degree <=2. Enumerate all monic linear/irreducible quadratic
    # squares and their nonzero multiples of degree at most four.
    factors = [[r,1] for r in range(P)]
    for b,c in product(range(P),repeat=2):
        if all((x*x+b*x+c)%P != 0 for x in range(P)):
            factors.append([c,b,1])
    assert len(factors)==6
    out=set()
    for f in factors:
        sq=multiply(f,f)
        for q in product(range(P),repeat=5-2*(len(f)-1)):
            if any(q):
                coeff=multiply(sq,q)
                assert len(coeff)==5
                out.add(tuple(coeff))
    return out


def packed_mask(bits):
    buf=bytearray(DOMAIN//8)
    for n,bit in enumerate(bits):
        if bit:
            buf[n>>3] |= 1<<(n&7)
    return int.from_bytes(buf,"little")


def audit():
    oracle=square_multiple_oracle()
    # Exhaustively cross-check the algebraic rule on all 3^5 coefficient
    # vectors, independently of their decimal representatives.
    for c in product(range(P),repeat=5):
        assert repeated_factor(c)==(c in oracle)
    bits=[]
    for n in range(DOMAIN):
        c=tuple(int(d)%P for d in f"{n:05d}")
        b=int(repeated_factor(c))
        assert b==int(c in oracle)
        bits.append(b)
    bitmap=packed_mask(bits)
    assert bitmap.bit_count()==sum(bits)
    old=existing_static_masks()
    manifest=[{"name":name,"sha256":digest(m)} for name,m in old]
    assert sha256(json.dumps(manifest,sort_keys=True,separators=(",",":")).encode()).hexdigest()==STATIC_MASK_MANIFEST_SHA256
    math=list(zip(RULE_NAMES,masks(),strict=True))
    hankel=packed_mask(int(determinant(n)>0) for n in range(DOMAIN))
    assert hankel.bit_count()==15053
    math.append(("det_H_gt_0",hankel))
    baseline=old+math
    groups=signatures_and_groups(baseline)
    assert len(baseline)==69 and len(groups)==93568
    novelty=_partition(groups,bits)
    direct=sum(sum(bits[n] for n in g)*(len(g)-sum(bits[n] for n in g)) for g in groups.values())
    assert direct==novelty["newly_distinguished_pairs"]
    assert novelty["old_indistinguishable_pairs"]==33791
    refined=Counter((key,bits[n]) for key,g in groups.items() for n in g)
    assert sum(refined.values())==DOMAIN
    assert sum(k*(k-1)//2 for k in refined.values())+direct==33791
    assert len(refined)==len(groups)+novelty["split_old_classes"]
    witness=novelty["witness_ids"]
    if witness is not None:
        a,b=witness
        assert all(((m>>a)&1)==((m>>b)&1) for _,m in baseline)
        assert bits[a]!=bits[b]
    atoms=signatures_and_groups(math)
    small_before=sum(len(g) for g in atoms.values() if len(g)<=100)
    assert small_before==9230
    counts=Counter((key,bits[n]) for key,g in atoms.items() for n in g)
    small_after=sum(k for k in counts.values() if k<=100)
    assert small_before<=small_after
    return {
        "schema":"pl5-squarefactor-v3761-1",
        "source":"INTERNAL/AI_AUTHORED",
        "domain":DOMAIN,"modulus":3,
        "rule":"nonzero polynomial has repeated irreducible factor",
        "coefficient_order":"ascending degree from leftmost decimal digit",
        "residue_vectors":243,"accepted_residue_vectors":len(oracle),
        "standalone_k":sum(bits),"standalone_sha256":digest(bitmap),
        "baseline_rule_count":len(baseline),
        "baseline_manifest":[{"name":name,"sha256":digest(m)} for name,m in baseline],
        "old_classes":len(groups),"new_classes":len(refined),
        "static_independence":novelty,
        "remaining_indistinguishable_pairs":33791-direct,
        "eleven_rule_small_atom_union_k":small_before,
        "twelve_rule_small_atom_union_k":small_after,
        "small_atom_union_is_not_one_capped_filter":True,
        "historical_coverage_measured":False,
        "practical_filter_value_proven":False
    }


class Tests(unittest.TestCase):
    def test_known_polynomials(self):
        self.assertFalse(repeated_factor([0]*5))
        self.assertFalse(repeated_factor([2]))
        self.assertFalse(repeated_factor([1,0,1]))
        self.assertTrue(repeated_factor([1,2,1]))
        self.assertTrue(repeated_factor([1,0,0,1])) # zero derivative
        self.assertTrue(repeated_factor([1,0,2,0,1]))
        self.assertFalse(repeated_factor([0,1]))
    def test_residue_oracle(self):
        oracle=square_multiple_oracle()
        self.assertEqual({c for c in product(range(3),repeat=5) if repeated_factor(c)},oracle)
    def test_full_domain(self):
        r=audit()
        self.assertEqual(r["baseline_rule_count"],69)
        self.assertEqual(r["static_independence"]["boolean_novelty_proven"],
                         r["static_independence"]["newly_distinguished_pairs"]>0)
        self.assertEqual(r["standalone_k"],sum(int(repeated_factor(tuple(map(int,f"{n:05d}")))) for n in range(DOMAIN)))

if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3761_SQUAREFACTOR_JSON="+json.dumps(audit(),sort_keys=True))
