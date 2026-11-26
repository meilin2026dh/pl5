"""V3.8.11: finite-field curvature-rank structural audit.
INTERNAL/AI_AUTHORED. Fixed static predicates; no historical inputs.

Second differences define a surjective linear map F_5^5 -> F_5^3:
choose the first two symbols freely, then reconstruct by recurrence.
For (a,b,c) in F_5^3, ac=b^2 has 25 solutions: 20 with a!=0
and 5 with a=b=0. The control b=0 also has 25 solutions.
Each field word has 2^5 decimal representatives, hence both predicates
have exactly 20000 positives. Both are invariant under affine trends.
No novelty, runtime, or operational filtering claim.
"""
from collections import Counter
from itertools import product
import json
import unittest

from graph_refinement_v3804 import cycle_rank, report
from local_return_refinement_v3807 import raw_aba
from reciprocal_redundancy_v3806 import local_return


def curvature(ds):
    if len(ds)!=5:
        raise ValueError("expected five symbols")
    a,b,c=tuple((ds[i]-2*ds[i+1]+ds[i+2])%5 for i in range(3))
    return (a*c-b*b)%5==0,b==0


def independent(ds):
    first=[(b-a)%5 for a,b in zip(ds,ds[1:])]
    a,b,c=[(v-u)%5 for u,v in zip(first,first[1:])]
    # Linear dependence of columns (a,b),(b,c).
    rank_le_one=(a==b==0 or any((t*a-b)%5==0 and (t*b-c)%5==0
                              for t in range(5)))
    return rank_le_one,b==0


def summarize(rows):
    if any(len(r)!=4 or any(type(k) is not int or k<0 for k in r) for r in rows):
        raise ValueError("invalid contingency")
    determinant=report([(a+c,b+d) for a,b,c,d in rows],100)
    control=report([(a+b,c+d) for a,b,c,d in rows],100)
    d_given_c=report([p for a,b,c,d in rows for p in ((a,b),(c,d))],100)
    c_given_d=report([p for a,b,c,d in rows for p in ((a,c),(b,d))],100)
    joint=sum(sum(r[i]*r[j] for i in range(4) for j in range(i)) for r in rows)
    assert determinant["newly_distinguished_unordered_pairs"]+c_given_d["newly_distinguished_unordered_pairs"]==joint
    assert control["newly_distinguished_unordered_pairs"]+d_given_c["newly_distinguished_unordered_pairs"]==joint
    assert d_given_c["refined_classes"]==c_given_d["refined_classes"]
    return {"determinant":determinant,"control":control,
            "determinant_given_control":d_given_c,"control_given_determinant":c_given_d,
            "joint_distinguished_pairs":joint,
            "category_sizes":[sum(r[i] for r in rows) for i in range(4)]}


def audit():
    from signed_order_v3763 import freeze,partition,DOMAIN,digest
    _,raw,_=freeze()
    atoms,counts=partition(raw,DOMAIN)
    width=(DOMAIN+7)//8
    original=[m.to_bytes(width,"little") for m in raw]
    masks=[bytearray(width) for _ in range(64)]
    direct=Counter()
    for x in range(DOMAIN):
        ds=tuple(map(int,f"{x:05d}"))
        d,c=curvature(ds)
        assert (d,c)==independent(ds)
        assert (d,c)==curvature(tuple(v+2*i+1 for i,v in enumerate(ds)))
        flags=(len(set(ds))<5,cycle_rank(ds)>0,raw_aba(ds),local_return(ds))
        base=sum(int(v)<<i for i,v in enumerate(flags))
        cat=int(d)+2*int(c)
        masks[4*base+cat][x//8]|=1<<(x%8)
        s=sum(((m[x//8]>>(x%8))&1)<<i for i,m in enumerate(original))
        direct[s,base,cat]+=1
    packed=[int.from_bytes(m,"little") for m in masks]
    rows=[]
    for s,(atom,k) in enumerate(zip(atoms,counts)):
        if not k:
            continue
        block=[]
        for base in range(16):
            row=tuple((atom&packed[4*base+c]).bit_count() for c in range(4))
            assert row==tuple(direct[s,base,c] for c in range(4))
            if sum(row):
                block.append(row)
        assert sum(map(sum,block))==k
        rows.extend(block)
    r=summarize(rows)
    assert r["category_sizes"]==[67200,12800,12800,7200]
    assert r["determinant"]["positive_mask_size"]==r["control"]["positive_mask_size"]==20000
    return {"schema":"pl5-curvature-rank-v3811-1","source":"INTERNAL/AI_AUTHORED",
            "domain":DOMAIN,"baseline_coordinate_count":16,
            "base_classes":len(rows),"original_rule_mask_sha256":[digest(m) for m in raw],
            "result":r,"limitations":["fixed 12 mathematical rules plus four experimental predicates, not full inventory",
                "equal marginal size and one binary predicate each, not matched measured cost",
                "static partition refinement only; capped-class union is not one capped candidate set",
                "no historical inputs, operational selection, or novelty claim"]}


class Tests(unittest.TestCase):
    def test_field_domain(self):
        c=Counter()
        for ds in product(range(5),repeat=5):
            result=curvature(ds)
            self.assertEqual(result,independent(ds))
            self.assertEqual(result,curvature(ds[::-1]))
            self.assertEqual(result,curvature(tuple(v+3*i+2 for i,v in enumerate(ds))))
            c[result]+=1
        self.assertEqual(sum(k for (d,b),k in c.items() if d),625)
        self.assertEqual(sum(k for (d,b),k in c.items() if b),625)
    def test_rank_count(self):
        self.assertEqual(sum((a*c-b*b)%5==0 for a,b,c in product(range(5),repeat=3)),25)
    def test_toy(self):
        r=summarize([(2,3,4,5)])
        self.assertEqual(r["determinant_given_control"]["newly_distinguished_unordered_pairs"],26)
        self.assertEqual(r["control_given_determinant"]["newly_distinguished_unordered_pairs"],23)
    def test_domain(self):
        self.__class__.result=audit()


if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3811_CURVATURE_JSON="+json.dumps(Tests.result,sort_keys=True))
