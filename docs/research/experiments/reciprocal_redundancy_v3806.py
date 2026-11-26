"""V3.8.6: reciprocal directed edges versus run-collapsed local return.
INTERNAL/AI_AUTHORED. Static mathematical redundancy audit.

Collapse consecutive equal symbols; this preserves nonloop directed edges.
For a walk with <=4 nonloop edges, suppose edge i is the reverse of edge j,
i<j. If j-i=1 there is a local return. If j-i=2 the intervening edge
would be a loop, impossible. If j-i=3 the two intervening edges form a
two-edge closed walk, hence a local return. The converse holds for any
length: a local return traverses both directions of an edge.
Thus the predicates are equivalent for words of length <=5, but not in
general (e.g. 0,1,2,3,1,0).
"""
from collections import Counter
from itertools import product
from math import perm
import json
import unittest


def reciprocal(ds):
    edges={(a,b) for a,b in zip(ds,ds[1:]) if a!=b}
    return any((b,a) in edges for a,b in edges)


def local_return(ds):
    collapsed=tuple(d for i,d in enumerate(ds) if i==0 or d!=ds[i-1])
    return any(a==c for a,c in zip(collapsed,collapsed[2:]))


def canonical(ds):
    labels={}
    return tuple(labels.setdefault(d,len(labels)) for d in ds)


def audit(q=10):
    patterns=sorted({canonical(ds) for ds in product(range(5),repeat=5)})
    positive=Counter(len(set(ds)) for ds in patterns if reciprocal(ds))
    predicted=sum(perm(q,k)*v for k,v in positive.items() if k<=q)
    contingency=Counter()
    for ds in product(range(q),repeat=5):
        contingency[int(reciprocal(ds)),int(local_return(ds))]+=1
    assert sum(contingency.values())==q**5
    assert contingency[0,1]==contingency[1,0]==0
    assert contingency[1,1]==predicted
    return {"schema":"pl5-reciprocal-redundancy-v3806-1",
            "source":"INTERNAL/AI_AUTHORED","domain":q**5,
            "equality_patterns":len(patterns),"positive_patterns":sum(positive.values()),
            "positive_patterns_by_symbol_count":dict(sorted(positive.items())),
            "reciprocal_positive":contingency[1,1],
            "local_return_positive":contingency[1,1],
            "mismatch":contingency[0,1]+contingency[1,0],
            "count_from_patterns":predicted,
            "limitations":["exact equivalence on words of length at most five only",
                           "no new independent graph predicate relative to local-return control",
                           "no timing, historical coverage or production changes"]}


class Tests(unittest.TestCase):
    def test_short_words(self):
        for length in range(1,6):
            for ds in product(range(4),repeat=length):
                self.assertEqual(reciprocal(ds),local_return(ds))
    def test_length_six_counterexample(self):
        ds=(0,1,2,3,1,0)
        self.assertTrue(reciprocal(ds))
        self.assertFalse(local_return(ds))
    def test_loops_and_invariance(self):
        self.assertTrue(local_return((0,1,1,0,0)))
        self.assertFalse(local_return((0,0,1,1,2)))
        for ds in product(range(3),repeat=5):
            self.assertEqual(reciprocal(ds),reciprocal(ds[::-1]))
            self.assertEqual(local_return(ds),local_return(tuple(2-d for d in ds)))
    def test_full(self):
        r=audit()
        self.assertEqual(r["equality_patterns"],52)
        self.assertEqual(r["positive_patterns"],28)
        self.assertEqual(r["reciprocal_positive"],26190)
        self.assertEqual(r["mismatch"],0)
        self.__class__.result=r

if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3806_RECIPROCAL_JSON="+json.dumps(Tests.result,sort_keys=True))
