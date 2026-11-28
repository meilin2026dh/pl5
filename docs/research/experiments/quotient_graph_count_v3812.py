"""V3.8.12 supplementary combinatorial certificate: two-to-one quotient.

INTERNAL/AI_AUTHORED. Abstract five-symbol words over q pairs of labels.
No historical inputs, operational selection or new filter rule.

Each quotient word has a unique restricted-growth equality pattern p
and an ordered assignment of its k distinct labels to q labels.
There are (q)_k such assignments and 2**5 choices of lifts.
Transition-graph cycle ranks are invariant under label renaming.
Enumerating 52 patterns and their 32 lifts gives exact coefficients
for the four possible rank transitions, valid for every integer q>=1.
"""
from itertools import product
from collections import Counter
from math import perm
import json
import unittest


def canonical(word):
    labels={}
    return tuple(labels.setdefault(v,len(labels)) for v in word)


def rank(word):
    edges={frozenset((a,b)) for a,b in zip(word,word[1:]) if a!=b}
    return len(edges)-len(set(word))+1


TRANSITIONS=tuple(product(range(2),repeat=2))
EXPECTED=((32,0,0,0),(360,0,120,0),(512,88,64,136),
          (224,48,0,48),(32,0,0,0))


def coefficient_table():
    patterns=sorted({canonical(w) for w in product(range(5),repeat=5)})
    assert len(patterns)==52
    c=Counter()
    for p in patterns:
        for bits in product(range(2),repeat=5):
            lift=tuple(2*a+b for a,b in zip(p,bits))
            a,b=rank(lift),rank(p)
            assert (a,b) in TRANSITIONS
            c[len(set(p)),a,b]+=1
    assert sum(c.values())==1664
    return tuple(tuple(c[k,a,b] for a,b in TRANSITIONS) for k in range(1,6))


def formula(q,table):
    if type(q) is not int or q<1:
        raise ValueError("positive integer pair count required")
    return tuple(sum(row[j]*perm(q,k) for k,row in enumerate(table,1) if k<=q)
                 for j in range(4))


class Tests(unittest.TestCase):
    def test_coefficients(self):
        self.assertEqual(coefficient_table(),EXPECTED)
    def test_independent_full_enumeration(self):
        table=coefficient_table()
        for q in range(1,6):
            brute=Counter((rank(w),rank(tuple(x//2 for x in w)))
                          for w in product(range(2*q),repeat=5))
            self.assertEqual(formula(q,table),tuple(brute[t] for t in TRANSITIONS))
    def test_mass_and_decimal(self):
        table=coefficient_table()
        for q in (1,2,5,10,100):
            self.assertEqual(sum(formula(q,table)),(2*q)**5)
        self.assertEqual(formula(5,table),(68800,11040,6240,13920))
        self.__class__.result={"schema":"finite-pair-quotient-count-v3812-1",
            "source":"INTERNAL/AI_AUTHORED","patterns":52,"lift_patterns":1664,
            "coefficient_rows_by_distinct_quotient_labels":table,
            "transition_order":TRANSITIONS,"decimal_counts":formula(5,table),
            "exhaustive_pair_counts":[1,2,3,4,5],
            "limitations":["uniform two-element fibers and five-symbol words only",
               "marginal structural counts, not contribution or execution performance",
               "no historical coverage or operational selection"]}


if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3812_COUNT_JSON="+json.dumps(Tests.result,sort_keys=True))
