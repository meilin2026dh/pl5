"""INTERNAL/AI_AUTHORED: exact five-position graph-transition counting.
For a nested equality partition with k coarse blocks containing m_i fine
blocks, assign distinct quotient labels j to its labeled coarse blocks.
The weight is sum_injective_assignments product_i perm(r_j, m_i).
A subset DP processes quotient labels once, either unused or assigned to
one vacant block. Each assignment is counted once. For fixed length five,
this avoids enumeration of words and permutations of quotient labels.
Static structural certificate only; no empirical coverage or speed claim.
"""
from collections import Counter
from itertools import product
from math import perm
import json
import unittest


def patterns(n):
    if n == 0:
        yield ()
    else:
        for p in patterns(n-1):
            for j in range(max(p, default=-1)+2):
                yield p+(j,)


def rank(w):
    return len({frozenset((a,b)) for a,b in zip(w,w[1:]) if a!=b})-len(set(w))+1


def table():
    ps=list(patterns(5))
    out=Counter()
    for p,q in product(ps, repeat=2):
        if any(p[i]==p[j] and q[i]!=q[j] for i in range(5) for j in range(i)):
            continue
        sizes=tuple(sorted(len({p[i] for i in range(5) if q[i]==j}) for j in range(max(q)+1)))
        out[rank(p),rank(q),sizes]+=1
    assert sum(out.values())==358
    return out


def weight(fibers, sizes):
    k=len(sizes)
    dp=[1]+[0]*((1<<k)-1)
    for r in fibers:
        nxt=dp.copy()
        for mask,v in enumerate(dp):
            for i,m in enumerate(sizes):
                if not mask & (1<<i):
                    nxt[mask | (1<<i)]+=v*perm(r,m)
        dp=nxt
    return dp[-1]


def counts(fibers):
    fibers=tuple(fibers)
    if not fibers or any(type(r) is not int or r<1 for r in fibers):
        raise ValueError('nonempty positive integer fibers required')
    out=[0]*4
    for (a,b,s),n in table().items():
        out[2*a+b]+=n*weight(fibers,s)
    assert sum(out)==sum(fibers)**5
    return tuple(out)


def oracle(fibers):
    labels=tuple(j for j,r in enumerate(fibers) for _ in range(r))
    out=Counter()
    for w in product(range(len(labels)), repeat=5):
        out[rank(w),rank(tuple(labels[i] for i in w))]+=1
    return tuple(out[a,b] for a,b in product(range(2),repeat=2))


class Tests(unittest.TestCase):
    def test_exhaustive_small(self):
        for q in range(1,5):
            for rs in product((1,2,3),repeat=q):
                if sum(rs)<=8:
                    self.assertEqual(counts(rs),oracle(rs),rs)
    def test_uniform_and_relabel(self):
        for rs in [(1,2,3),(3,1,2),(2,2,2),(1,1,1),(6,)]:
            self.assertEqual(counts(rs),oracle(rs))
            self.assertEqual(counts(rs),counts(rs[::-1]))
        self.assertEqual(counts((2,)*5),(68800,11040,6240,13920))
    def test_weight(self):
        from itertools import permutations
        for rs in [(1,2,4),(3,2,1,4),(1,)]:
            for _,_,s in table():
                expected=sum(__import__('math').prod(perm(r,m) for r,m in zip(xs,s)) for xs in permutations(rs,len(s)))
                self.assertEqual(weight(rs,s),expected)
    def test_invalid_and_large(self):
        for rs in [(),(0,),(-1,),(True,),(1.5,)]:
            with self.assertRaises(ValueError): counts(rs)
        self.assertEqual(sum(counts((1,2,3,100,1000)*10)),11060**5)
        self.assertEqual(counts((1,)*100)[1:3],(0,0))


if __name__=='__main__':
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print('NONUNIFORM_QUOTIENT_JSON='+json.dumps({'source':'INTERNAL/AI_AUTHORED','nested_patterns':358,'unequal_small':counts((1,2,3)), 'limitations':['static counting only','no historical data','no measured cost advantage']},sort_keys=True))
