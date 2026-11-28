"""V3.7.82: exact static exclusion coverage attribution.
INTERNAL/AI_AUTHORED. Fixed positive retention sets, no temporal records.
"""
from fractions import Fraction
from math import comb
import json
import unittest
from signed_order_v3763 import freeze, partition, DOMAIN, digest
from static_entropy_v3773 import subset_entropies, decompose


def exclusion_audit(raw,size):
    n=len(raw)
    if not 1<=n<=12 or size<=0 or any(m<0 or m.bit_length()>size for m in raw):
        raise ValueError("invalid bounded domain")
    full=(1<<size)-1
    all_rules=(1<<n)-1
    intersections=[full]*(1<<n)
    for s in range(1,1<<n):
        b=s & -s
        intersections[s]=intersections[s^b]&raw[b.bit_length()-1]
    v=[size-m.bit_count() for m in intersections]
    _,counts=partition(raw,size)
    # An excluded identity contributes 1/r to each of its r excluding rules.
    shares=[Fraction(0) for _ in raw]
    multiplicity=[0]*(n+1)
    for signature,k in enumerate(counts):
        excluded=all_rules^signature
        r=excluded.bit_count()
        multiplicity[r]+=k
        if r and k:
            for j in range(n):
                if excluded>>j&1:
                    shares[j]+=Fraction(k,r)
    rows=[]
    for j in range(n):
        b=1<<j
        reference=sum((Fraction(v[s|b]-v[s],n*comb(n-1,s.bit_count()))
                       for s in range(1<<n) if not s&b),Fraction(0))
        assert reference==shares[j]
        exclusive=v[-1]-v[all_rules^b]
        singleton=v[b]
        assert 0<=exclusive<=reference<=singleton
        rows.append({"singleton_excluded":singleton,"exclusive_excluded":exclusive,
                     "overlapping_excluded":singleton-exclusive,
                     "shapley_exact":str(reference),"shapley_float":float(reference)})
    assert sum(shares)==v[-1] and sum(multiplicity)==size
    assert multiplicity[0]==size-v[-1]
    assert sum(x["exclusive_excluded"] for x in rows)==multiplicity[1]
    # Independent counts derived from truth signatures for every coalition.
    for s,k in enumerate(v):
        assert k==size-sum(c for t,c in enumerate(counts) if t&s==s)
    return rows,multiplicity,v,counts


def audit():
    names,raw,_=freeze()
    rows,multiplicity,v,counts=exclusion_audit(raw,DOMAIN)
    entropy,_=decompose(subset_entropies(counts,len(raw)),len(raw))
    for j,row in enumerate(rows):
        row["name"]=names[j]
        row["entropy_shapley_bits"]=entropy[j]["shapley_bits"]
    return {"schema":"pl5-static-exclusion-v3782-1","source":"INTERNAL/AI_AUTHORED",
            "domain":DOMAIN,"coalitions":len(v),"union_excluded":v[-1],
            "intersection_retained":DOMAIN-v[-1],"exclusion_multiplicity":multiplicity,
            "rules":rows,"rule_mask_sha256":[digest(m) for m in raw],
            "limitations":["fixed positive retention sets only; polarity changes attribution",
            "coverage objective is monotone submodular; shared removal is not unique contribution",
            "empty intersection is not a useful compression solution",
            "entropy and exclusion attribution are different objectives",
            "static set analysis only; no historical coverage or removal policy"]}


class Tests(unittest.TestCase):
    def test_overlap(self):
        rows,m,v,_=exclusion_audit((0b1100,0b1010),4)
        self.assertEqual(m,[1,2,1])
        self.assertEqual([r["shapley_exact"] for r in rows],["3/2","3/2"])
        self.assertEqual([r["exclusive_excluded"] for r in rows],[1,1])
        self.assertEqual(v[-1],3)
    def test_duplicate_and_empty(self):
        rows,m,v,_=exclusion_audit((3,3,15),4)
        self.assertEqual([r["shapley_exact"] for r in rows],["1","1","0"])
        self.assertEqual(m,[2,0,2,0])
        self.assertEqual(exclusion_audit((0,15),4)[2][-1],4)
        with self.assertRaises(ValueError):
            exclusion_audit((16,),4)
    def test_full(self):
        r=audit()
        self.assertEqual(r["coalitions"],4096)
        self.assertEqual(len(r["rules"]),12)
        self.__class__.result=r


if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3782_EXCLUSION_JSON="+json.dumps(Tests.result,sort_keys=True))
