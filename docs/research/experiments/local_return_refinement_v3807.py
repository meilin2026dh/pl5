"""V3.8.7: conditional local-return refinement against direct ABA.
INTERNAL/AI_AUTHORED. Static aggregate structure only; no historical inputs.
"""
from collections import Counter
from itertools import product
from fractions import Fraction
import json
import unittest
from graph_refinement_v3804 import cycle_rank, cycle_dsu, report
from reciprocal_redundancy_v3806 import local_return, reciprocal


def raw_aba(ds):
    return any(a==c and a!=b for a,b,c in zip(ds,ds[1:],ds[2:]))


def summarize(rows,cap):
    # Each frozen class: no return, return after collapsing runs only,
    # or direct ABA. Direct ABA implies collapsed local return.
    if any(len(row)!=3 or any(k<0 for k in row) for row in rows):
        raise ValueError("invalid contingency")
    local=report([(a,b+c) for a,b,c in rows],cap)
    direct=report([(a+b,c) for a,b,c in rows],cap)
    conditional=report([pair for a,b,c in rows for pair in ((a,b),(c,0))],cap)
    assert conditional["refined_classes"]==sum(k>0 for row in rows for k in row)
    assert conditional["newly_distinguished_unordered_pairs"]==sum(a*b for a,b,c in rows)
    total=sum(sum(row) for row in rows)
    pairs=sum(sum(row)*(sum(row)-1)//2 for row in rows)
    k=local["positive_mask_size"]
    # Exact expectation for a uniformly random size-k binary partition.
    # Analytic descriptive comparator, not an observed performance test.
    expected=Fraction(pairs*2*k*(total-k),total*(total-1)) if total>1 else Fraction(0)
    return {"local_return":local,"direct_ABA":direct,
            "local_given_direct":conditional,"category_sizes":[sum(row[i] for row in rows) for i in range(3)],
            "matched_size_random_pair_expectation_exact":str(expected)}


def audit():
    from signed_order_v3763 import freeze,partition,DOMAIN,digest
    _,raw,_=freeze()
    atoms,counts=partition(raw,DOMAIN)
    width=(DOMAIN+7)//8
    packed=[m.to_bytes(width,"little") for m in raw]
    # Three categories for baseline repeat/cycle; three for new predicates.
    masks=[[bytearray(width) for _ in range(3)] for _ in range(3)]
    oracle=Counter()
    for x in range(DOMAIN):
        ds=tuple(map(int,f"{x:05d}"))
        cycle=cycle_rank(ds)>0
        assert cycle==cycle_dsu(ds)
        repeat=len(set(ds))<5
        ret=local_return(ds)
        direct=raw_aba(ds)
        assert ret==reciprocal(ds)
        assert not direct or ret
        assert not ret or repeat
        assert not cycle or repeat
        base=2 if cycle else int(repeat)
        cat=2 if direct else int(ret)
        masks[base][cat][x//8]|=1<<(x%8)
        signature=sum(((m[x//8]>>(x%8))&1)<<j for j,m in enumerate(packed))
        oracle[signature,base,cat]+=1
    bits=[[int.from_bytes(m,"little") for m in row] for row in masks]
    rows=[]
    for s,(atom,k) in enumerate(zip(atoms,counts)):
        block=[]
        for base in range(3):
            row=tuple((atom&m).bit_count() for m in bits[base])
            assert row==tuple(oracle[s,base,c] for c in range(3))
            block.append(row)
        assert sum(map(sum,block))==k
        rows.extend(block)
    r=summarize(rows,100)
    assert r["local_return"]["original_classes"]==2634
    assert r["local_return"]["positive_mask_size"]==26190
    return {"schema":"pl5-local-return-refinement-v3807-1",
            "source":"INTERNAL/AI_AUTHORED","domain":DOMAIN,
            "baseline_rule_count":14,"original_mask_sha256":[digest(m) for m in raw],
            "result":r,"limitations":["conditional static partition refinement only",
            "baseline is 12 frozen mathematical rules plus repeat and cycle, not full inventory",
            "direct ABA is a one-predicate control, not equal marginal size or measured cost",
            "random comparator is analytic expectation for pair distinction, not historical coverage",
            "capped-class union is not a single capped candidate set",
            "no historical inputs, operational selection or production changes"]}


class Tests(unittest.TestCase):
    def test_nesting(self):
        self.assertTrue(raw_aba((0,1,0,2,3)))
        self.assertFalse(raw_aba((0,1,1,0,2)))
        self.assertTrue(local_return((0,1,1,0,2)))
        for ds in product(range(4),repeat=5):
            self.assertFalse(raw_aba(ds) and not local_return(ds))
    def test_contribution(self):
        r=summarize([(2,3,4)],4)
        self.assertEqual(r["local_given_direct"]["newly_distinguished_unordered_pairs"],6)
        self.assertEqual(r["local_return"]["newly_distinguished_unordered_pairs"],14)
        self.assertEqual(r["direct_ABA"]["newly_distinguished_unordered_pairs"],20)
    def test_toy_exhaustive(self):
        for row in product(range(4),repeat=3):
            r=summarize([row],2)
            cats=[i for i,k in enumerate(row) for _ in range(k)]
            expected=sum((a==2)==(b==2) and (a>0)!=(b>0)
                         for i,a in enumerate(cats) for b in cats[:i])
            self.assertEqual(r["local_given_direct"]["newly_distinguished_unordered_pairs"],expected)
    def test_domain(self):
        self.__class__.result=audit()

if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3807_LOCAL_RETURN_JSON="+json.dumps(Tests.result,sort_keys=True))
