"""V3.8.5: conditional graph-cycle structural contribution.
INTERNAL/AI_AUTHORED. Static aggregate audit only; no historical inputs.
"""
from collections import Counter
from itertools import product
import json
import unittest
from graph_refinement_v3804 import cycle_rank, cycle_dsu, report


def summarize(rows, cap):
    # States: all distinct, repeated but acyclic, cyclic (implies repeated).
    for row in rows:
        if len(row)!=3 or any(k<0 for k in row):
            raise ValueError("invalid contingency")
    base_to_repeat=report([(a,b+c) for a,b,c in rows],cap)
    base_to_cycle=report([(a+b,c) for a,b,c in rows],cap)
    repeat_to_both=report([pair for a,b,c in rows for pair in ((a,0),(b,c))],cap)
    cycle_to_both=report([pair for a,b,c in rows for pair in ((a,b),(0,c))],cap)
    total_pairs= sum(a*b+a*c+b*c for a,b,c in rows)
    overlap=sum(a*c for a,b,c in rows)
    assert repeat_to_both["newly_distinguished_unordered_pairs"]==sum(b*c for a,b,c in rows)
    assert cycle_to_both["newly_distinguished_unordered_pairs"]==sum(a*b for a,b,c in rows)
    assert base_to_repeat["newly_distinguished_unordered_pairs"]+base_to_cycle["newly_distinguished_unordered_pairs"]-overlap==total_pairs
    assert base_to_repeat["newly_distinguished_unordered_pairs"]+repeat_to_both["newly_distinguished_unordered_pairs"]==total_pairs
    assert repeat_to_both["refined_classes"]==cycle_to_both["refined_classes"]
    assert repeat_to_both["capped_class_union_after"]==cycle_to_both["capped_class_union_after"]
    return {"repeat_alone":base_to_repeat,"cycle_alone":base_to_cycle,
            "cycle_given_repeat":repeat_to_both,"repeat_given_cycle":cycle_to_both,
            "joint_newly_distinguished_pairs":total_pairs,"shared_distinguished_pairs":overlap,
            "category_sizes":[sum(row[j] for row in rows) for j in range(3)]}


def audit():
    from signed_order_v3763 import freeze,partition,DOMAIN,digest
    names,raw,_=freeze()
    atoms,counts=partition(raw,DOMAIN)
    data=Counter()
    width=(DOMAIN+7)//8
    old=[m.to_bytes(width,"little") for m in raw]
    masks=[bytearray(width) for _ in range(3)]
    for x in range(DOMAIN):
        d=tuple(map(int,f"{x:05d}"))
        cycle=cycle_rank(d)>0
        assert cycle==cycle_dsu(d)
        repeat=len(set(d))<5
        assert not cycle or repeat
        cat=2 if cycle else int(repeat)
        signature=sum(((m[x//8]>>(x%8))&1)<<j for j,m in enumerate(old))
        data[signature,cat]+=1
        masks[cat][x//8]|=1<<(x%8)
    category_masks=[int.from_bytes(m,"little") for m in masks]
    rows=[]
    for s,(atom,k) in enumerate(zip(atoms,counts)):
        row=tuple((atom&m).bit_count() for m in category_masks)
        assert row==tuple(data[s,c] for c in range(3))
        assert sum(row)==k
        rows.append(row)
    r=summarize(rows,100)
    assert r["category_sizes"]==[30240,49600,20160]
    assert r["repeat_alone"]["refined_classes"]==1912
    assert r["cycle_alone"]["refined_classes"]==1813
    return {"schema":"pl5-conditional-graph-v3805-1","source":"INTERNAL/AI_AUTHORED",
            "domain":DOMAIN,"baseline_rule_count":len(raw),
            "rule_mask_sha256":[digest(m) for m in raw],"result":r,
            "limitations":["conditional structural contribution, not an operational filtering policy",
            "only frozen 12-rule baseline plus repeat predicate, not whole inventory",
            "capped-class union is not one capped candidate set",
            "no historical inputs, matched-cost performance or generalization claims"]}


class Tests(unittest.TestCase):
    def test_contingency(self):
        r=summarize([(2,3,4)],4)
        self.assertEqual(r["cycle_given_repeat"]["newly_distinguished_unordered_pairs"],12)
        self.assertEqual(r["repeat_given_cycle"]["newly_distinguished_unordered_pairs"],6)
        self.assertEqual(r["shared_distinguished_pairs"],8)
        self.assertEqual(r["joint_newly_distinguished_pairs"],26)
    def test_redundant_conditional(self):
        r=summarize([(1,0,3),(2,4,0)],3)
        self.assertEqual(r["cycle_given_repeat"]["split_classes"],0)
    def test_exhaustive_toy(self):
        for row in product(range(4),repeat=3):
            r=summarize([row],2)
            cats=[j for j,k in enumerate(row) for _ in range(k)]
            brute=sum((a>0)==(b>0) and (a==2)!=(b==2)
                      for i,a in enumerate(cats) for b in cats[:i])
            self.assertEqual(r["cycle_given_repeat"]["newly_distinguished_unordered_pairs"],brute)
    def test_domain(self):
        self.__class__.result=audit()

if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3805_CONDITIONAL_GRAPH_JSON="+json.dumps(Tests.result,sort_keys=True))
