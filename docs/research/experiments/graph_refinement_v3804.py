"""V3.8.4: static graph-cycle refinement of frozen Boolean signatures.
INTERNAL/AI_AUTHORED. No historical inputs or operational selection policy.
One binary graph predicate versus one binary repeated-symbol predicate.
"""
from collections import Counter
from itertools import product
import json
import unittest

def cycle_rank(digits):
    # The undirected simple transition graph of a walk is connected.
    # Self-loops are omitted; repeated undirected edges count only once.
    edges={tuple(sorted((a,b))) for a,b in zip(digits,digits[1:]) if a!=b}
    return len(edges)-len(set(digits))+1

def cycle_dsu(digits):
    parent={d:d for d in digits}
    def root(x):
        while parent[x]!=x:
            x=parent[x]
        return x
    seen=set()
    for a,b in zip(digits,digits[1:]):
        if a==b:
            continue
        edge=(min(a,b),max(a,b))
        if edge in seen:
            continue
        seen.add(edge)
        x,y=root(a),root(b)
        if x==y:
            return True
        parent[x]=y
    return False

def report(groups,cap):
    sizes=[a+b for a,b in groups]
    before=sum(k>0 for k in sizes)
    after=sum(a>0 for a,b in groups)+sum(b>0 for a,b in groups)
    split=sum(a>0 and b>0 for a,b in groups)
    pairs=sum(a*b for a,b in groups)
    assert after-before==split
    choose2=lambda k:k*(k-1)//2
    assert pairs==sum(choose2(a+b)-choose2(a)-choose2(b) for a,b in groups)
    cap_before=sum(k for k in sizes if 0<k<=cap)
    cap_after=sum(k for row in groups for k in row if 0<k<=cap)
    assert cap_after>=cap_before
    return {"original_classes":before,"refined_classes":after,
            "split_classes":split,"newly_distinguished_unordered_pairs":pairs,
            "remaining_indistinguishable_pairs":sum(choose2(k) for row in groups for k in row),
            "positive_mask_size":sum(b for a,b in groups),
            "capped_class_union_before":cap_before,
            "capped_class_union_after":cap_after,
            "capped_class_union_gain":cap_after-cap_before}

def evaluate(raw,size,cap,partition):
    masks=[bytearray((size+7)//8) for _ in range(2)]
    oracle=[Counter(),Counter()]
    old=[m.to_bytes((size+7)//8,"little") for m in raw]
    for x in range(size):
        digits=tuple(map(int,f"{x:05d}"))
        graph=cycle_rank(digits)>0
        assert graph==cycle_dsu(digits)
        repeat=len(set(digits))<len(digits)
        assert not graph or repeat
        signature=sum(((m[x//8]>>(x%8))&1)<<j for j,m in enumerate(old))
        for j,truth in enumerate((graph,repeat)):
            if truth:
                masks[j][x//8]|=1<<(x%8)
            oracle[j][signature,int(truth)]+=1
    atoms,counts=partition(raw,size)
    rows=[]
    for j,m in enumerate(masks):
        mask=int.from_bytes(m,"little")
        groups=[]
        for s,(atom,k) in enumerate(zip(atoms,counts)):
            b=(atom&mask).bit_count()
            a=k-b
            assert (a,b)==(oracle[j][s,0],oracle[j][s,1])
            groups.append((a,b))
        rows.append(report(groups,cap))
    return rows

def audit():
    from signed_order_v3763 import freeze,partition,DOMAIN,digest
    names,raw,_=freeze()
    graph,repeat=evaluate(raw,DOMAIN,100,partition)
    assert graph["original_classes"]==repeat["original_classes"]==1079
    return {"schema":"pl5-static-graph-refinement-v3804-1",
            "source":"INTERNAL/AI_AUTHORED","domain":DOMAIN,
            "baseline_rule_count":len(raw),"rule_mask_sha256":[digest(m) for m in raw],
            "graph_cycle":graph,"repeat_symbol_control":repeat,
            "limitations":["static partition refinement only",
              "one binary predicate each, not matched marginal size or measured cost",
              "capped-class union is not one capped candidate set",
              "independence relative to frozen 12 rules only, not full repository inventory",
              "no historical coverage, no operational selection, no claim of mathematical novelty"]}

class Tests(unittest.TestCase):
    def test_examples(self):
        self.assertFalse(cycle_dsu((0,1,0,1,0)))
        self.assertTrue(cycle_dsu((0,1,2,0,0)))
        self.assertEqual(cycle_rank((0,1,2,3,0)),1)
        self.assertEqual(cycle_rank((7,7,7,7,7)),0)
    def test_small_exhaustive_and_invariance(self):
        for d in product(range(4),repeat=5):
            self.assertEqual(cycle_rank(d)>0,cycle_dsu(d))
            self.assertEqual(cycle_rank(d),cycle_rank(d[::-1]))
            self.assertEqual(cycle_rank(d),cycle_rank(tuple(3-x for x in d)))
    def test_split_identity(self):
        r=report([(2,3),(0,4),(1,0)],3)
        self.assertEqual(r["split_classes"],1)
        self.assertEqual(r["newly_distinguished_unordered_pairs"],6)
        self.assertEqual(r["capped_class_union_gain"],5)
    def test_frozen(self):
        r=audit()
        self.assertEqual(r["domain"],100000)
        self.__class__.result=r

if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3804_GRAPH_JSON="+json.dumps(Tests.result,sort_keys=True))
