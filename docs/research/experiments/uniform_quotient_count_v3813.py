"""V3.8.13: exact structural transition counts for uniform quotient fibers.
INTERNAL/AI_AUTHORED. Abstract five-symbol words; static structural counts.

For q quotient labels each with r preimages, a pair of nested equality
partitions P (fine), Q (coarse) contributes (q)_k * product_j (r)_{m_j},
where k is the number of Q blocks and m_j counts P blocks in Q block j.
Every word has exactly one such nested pair; assignments are injective
within each relevant label set. The 358 nested patterns exhaust all
cases, independently of q and r. Cycle ranks depend only on these
patterns. No new filter rule or empirical coverage claim.
"""
from collections import Counter
from itertools import product
from math import perm, prod
import json
import unittest
from quotient_graph_count_v3812 import formula, coefficient_table


def patterns(n):
    if n == 0:
        yield ()
        return
    for p in patterns(n-1):
        for j in range(max(p,default=-1)+2):
            yield p+(j,)


def rank(w):
    edges={frozenset((a,b)) for a,b in zip(w,w[1:]) if a!=b}
    return len(edges)-len(set(w))+1


def nested_table():
    ps=list(patterns(5))
    assert len(ps)==52
    out=Counter()
    for q in ps:
        for p in ps:
            if any(p[i]==p[j] and q[i]!=q[j] for i in range(5) for j in range(i)):
                continue
            sizes=tuple(sorted(len({p[i] for i in range(5) if q[i]==j})
                               for j in range(max(q)+1)))
            out[rank(p),rank(q),sizes]+=1
    assert sum(out.values())==358
    return out


def counts(q,r,table=None):
    if any(type(x) is not int or x<1 for x in (q,r)):
        raise ValueError("positive integers required")
    table=nested_table() if table is None else table
    out=[0]*4
    for (a,b,sizes),n in table.items():
        out[2*a+b]+=n*perm(q,len(sizes))*prod(perm(r,s) for s in sizes)
    assert sum(out)==(q*r)**5
    return tuple(out)


def closed_gain_loss(q,r):
    a,b,c,d=(perm(r,i) for i in range(1,5))
    gain=perm(q,3)*(6*a*a*b+2*a*a*c+5*a*b*b)+perm(q,4)*3*a*a*a*b
    loss=q*(7*c+3*d)+perm(q,2)*(12*a*c+21*a*b+9*b*b)+perm(q,3)*8*a*a*b
    return gain,loss


def oracle(q,r):
    out=Counter()
    for w in product(range(q*r),repeat=5):
        out[rank(w),rank(tuple(v//r for v in w))]+=1
    return tuple(out[a,b] for a,b in product(range(2),repeat=2))


class Tests(unittest.TestCase):
    def test_coefficients(self):
        t=nested_table()
        self.assertEqual({s:n for (a,b,s),n in t.items() if (a,b)==(0,1)},
                         {(1,1,2):6,(1,1,3):2,(1,2,2):5,(1,1,1,2):3})
        self.assertEqual({s:n for (a,b,s),n in t.items() if (a,b)==(1,0)},
                         {(3,):7,(4,):3,(1,3):12,(1,2):21,(2,2):9,(1,1,2):8})
    def test_full_words(self):
        table=nested_table()
        cases=[(q,r) for q in range(1,5) for r in range(1,4)]+[(5,2)]
        for q,r in cases:
            result=counts(q,r,table)
            self.assertEqual(result,oracle(q,r),(q,r))
            self.assertEqual(result[1:3],closed_gain_loss(q,r))
        self.__class__.cases=cases
    def test_prior_certificate(self):
        table=nested_table()
        prior=coefficient_table()
        for q in range(1,21):
            self.assertEqual(counts(q,2,table),formula(q,prior))
            self.assertEqual(counts(q,1,table)[1:3],(0,0))
    def test_formula_large(self):
        table=nested_table()
        for q,r in product((1,2,3,5,10,100),repeat=2):
            self.assertEqual(counts(q,r,table)[1:3],closed_gain_loss(q,r))
        self.assertEqual(counts(5,2,table),(68800,11040,6240,13920))


if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3813_UNIFORM_QUOTIENT_JSON="+json.dumps({
        "schema":"uniform-quotient-count-v3813-1","source":"INTERNAL/AI_AUTHORED",
        "nested_patterns":358,"full_word_oracle_cases":Tests.cases,
        "decimal_specialization":counts(5,2),
        "coefficient_rows":[[a,b,list(s),n] for (a,b,s),n in sorted(nested_table().items())],
        "limitations":["five-symbol words with uniform finite fibers only",
                       "static structural counting, not a new filter rule",
                       "no coverage or computation-cost advantage established"]},sort_keys=True))
