"""V3.8.1: distinguish linear rank from Boolean expressive redundancy.
INTERNAL/AI_AUTHORED. Static aggregate audit, no historical inputs or new rules.

For a nonempty realized signature set R, a coordinate subset S preserves
the Boolean algebra iff projection onto S is injective on R. Necessity:
a collision cannot be distinguished by any Boolean expression on S.
Sufficiency: each projected row is isolated by its signed conjunction,
and arbitrary unions of these conjunctions recover every old expression.
Equivalently S must hit every nonzero pairwise XOR difference.
The affine GF(2) and rational ranks (with a constant column, minus one)
are upper bounds on the minimum coordinate count, not exact Boolean ranks:
a linear column basis recovers every column, while nonlinear dependencies
can make a strictly smaller Boolean basis sufficient.
"""
from fractions import Fraction
from collections import Counter
import json
import unittest


def affine_rank(rows,n,field):
    basis={}
    for r in rows:
        if field=="F2":
            v=r | (1<<n)
            while v:
                j=v.bit_length()-1
                if j not in basis:
                    basis[j]=v
                    break
                v ^= basis[j]
        elif field=="Q":
            v=[Fraction((r>>j)&1) for j in range(n)]+[Fraction(1)]
            for j,b in sorted(basis.items()):
                if v[j]:
                    c=v[j]
                    v=[x-c*y for x,y in zip(v,b)]
            j=next((j for j,x in enumerate(v) if x),None)
            if j is not None:
                c=v[j]
                basis[j]=[x/c for x in v]
        else:
            raise ValueError("unsupported field")
        if len(basis)==n+1:
            break
    return len(basis)-1


def analyze(rows,n):
    rows=sorted(set(rows))
    if not 1<=n<=12 or not rows or rows[0]<0 or rows[-1]>=1<<n:
        raise ValueError("invalid realized signatures")
    full=(1<<n)-1
    # Primary oracle: projected class counts for every coordinate subset.
    projections=[len({r&s for r in rows}) for s in range(full+1)]
    # Independent oracle: difference-support collision criterion.
    diffs=set()
    for i,r in enumerate(rows):
        for t in rows[:i]:
            diffs.add(r^t)
    collisions=[int(d in diffs) for d in range(full+1)]
    for j in range(n):
        b=1<<j
        for s in range(full+1):
            if s&b:
                collisions[s]+=collisions[s^b]
    sufficient=[s for s,k in enumerate(projections) if k==len(rows)]
    assert sufficient==[s for s in range(full+1) if collisions[full^s]==0]
    minimum=min(s.bit_count() for s in sufficient)
    essential=sum(1<<j for j in range(n) if (1<<j) in diffs)
    assert essential==sum(1<<j for j in range(n)
                          if projections[full^(1<<j)]<len(rows))
    gf2=affine_rank(rows,n,"F2")
    rational=affine_rank(rows,n,"Q")
    lower=(len(rows)-1).bit_length()
    assert lower<=minimum<=min(gf2,rational)<=n
    return {"occupied_classes":len(rows),"coordinate_count":n,
            "information_lower_bound":lower,"minimum_boolean_coordinate_count":minimum,
            "affine_rank_F2":gf2,"affine_rank_Q":rational,
            "minimum_basis_count":sum(s.bit_count()==minimum for s in sufficient),
            "essential_coordinate_count":essential.bit_count(),
            "sufficient_subset_count":len(sufficient),
            "checked_subsets":len(projections),
            "projection_class_count_by_width":{
                str(k):{"min":min(projections[s] for s in range(full+1) if s.bit_count()==k),
                        "max":max(projections[s] for s in range(full+1) if s.bit_count()==k)}
                for k in range(n+1)}}


def audit():
    from signed_order_v3763 import freeze, partition, DOMAIN, digest
    names,raw,_=freeze()
    _,counts=partition(raw,DOMAIN)
    # The report contains only aggregate structure metrics, not identities
    # or an operational rule-selection policy.
    r=analyze([s for s,k in enumerate(counts) if k],len(raw))
    return {"schema":"pl5-boolean-rank-audit-v3801-1",
            "source":"INTERNAL/AI_AUTHORED","domain":DOMAIN,
            "rule_mask_sha256":[digest(m) for m in raw],
            "result":r,
            "limitations":["frozen twelve-coordinate inventory only",
                "Boolean basis preserves expression space, not individual evaluation cost",
                "linear rank is not a substitute for Boolean equivalence",
                "no new filtering rule or historical coverage measurement"]}


class Tests(unittest.TestCase):
    def test_nonlinear_redundancy(self):
        # Third coordinate is AND of the first two.
        r=analyze([0,1,2,7],3)
        self.assertEqual(r["minimum_boolean_coordinate_count"],2)
        self.assertEqual(r["affine_rank_F2"],3)
        self.assertEqual(r["affine_rank_Q"],3)
        self.assertEqual(r["minimum_basis_count"],1)
    def test_field_dependence(self):
        # Third coordinate is XOR of the first two.
        r=analyze([0,3,5,6],3)
        self.assertEqual(r["minimum_boolean_coordinate_count"],2)
        self.assertEqual(r["affine_rank_F2"],2)
        self.assertEqual(r["affine_rank_Q"],3)
        self.assertEqual(r["minimum_basis_count"],3)
    def test_constant_and_essential(self):
        r=analyze([7],3)
        self.assertEqual(r["minimum_boolean_coordinate_count"],0)
        self.assertEqual(r["affine_rank_Q"],0)
        self.assertEqual(r["minimum_basis_count"],1)
        r=analyze([0,1,2,4],3)
        self.assertEqual(r["essential_coordinate_count"],3)
        self.assertEqual(r["minimum_boolean_coordinate_count"],3)
        with self.assertRaises(ValueError):
            analyze([],3)
    def test_exhaustive_small(self):
        # Every nonempty realized signature set on three coordinates.
        for mask in range(1,256):
            analyze([r for r in range(8) if mask>>r&1],3)
    def test_frozen(self):
        r=audit()
        self.assertEqual(r["result"]["checked_subsets"],4096)
        self.__class__.result=r


if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3801_BOOLEAN_RANK_JSON="+json.dumps(Tests.result,sort_keys=True))
