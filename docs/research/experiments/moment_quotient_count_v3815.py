"""INTERNAL/AI_AUTHORED: moment-based exact count certificate for finite graphs.

For labeled coarse blocks with fine-block counts m_i, injective assignment
weights are obtained by Mobius inversion on set partitions of coarse blocks.
For a block B of that partition, the polynomial prod_i (r)_{m_i}
has degree <=5. Its sum over fibers depends only on power sums S_1..S_5.
Thus a five-position graph transition histogram is determined by those five
moments. This is a static count certificate, not a new filter rule.
"""
from collections import Counter
from functools import lru_cache
from itertools import product
from math import factorial, prod
import json
import unittest
from nonuniform_quotient_count_v3814 import counts as subset_counts, table, oracle


def partitions(n):
    if n == 0:
        yield ()
    else:
        for p in partitions(n-1):
            yield p+((n-1,),)
            for i in range(len(p)):
                yield p[:i]+(p[i]+(n-1,),)+p[i+1:]


@lru_cache(maxsize=None)
def polynomial(sizes):
    p=[1]
    for m in sizes:
        for j in range(m):
            out=[0]*(len(p)+1)
            for d,c in enumerate(p):
                out[d]-=j*c
                out[d+1]+=c
            p=out
    return tuple(p)


@lru_cache(maxsize=None)
def inversion_terms(sizes):
    out=Counter()
    for p in partitions(len(sizes)):
        mu=prod((-1)**(len(b)-1)*factorial(len(b)-1) for b in p)
        key=tuple(sorted(tuple(sorted(sizes[i] for i in b)) for b in p))
        out[key]+=mu
    return tuple(sorted((key,c) for key,c in out.items() if c))


def moments(fibers):
    fibers=tuple(fibers)
    if not fibers or any(type(r) is not int or r<1 for r in fibers):
        raise ValueError('nonempty positive integer fibers required')
    return tuple(sum(r**d for r in fibers) for d in range(1,6))


def evaluate(s):
    @lru_cache(maxsize=None)
    def block_sum(b):
        return sum(c*s[d-1] for d,c in enumerate(polynomial(b)) if d)
    @lru_cache(maxsize=None)
    def weight(sizes):
        return sum(c*prod(block_sum(b) for b in key) for key,c in inversion_terms(sizes))
    out=[0]*4
    for (a,b,sizes),n in table().items():
        out[2*a+b]+=n*weight(sizes)
    assert min(out)>=0 and sum(out)==s[0]**5
    return tuple(out)


def counts(fibers):
    return evaluate(moments(fibers))


def integer_partitions(n, lo=1):
    if n==0:
        yield ()
    else:
        for a in range(lo,n+1):
            for rest in integer_partitions(n-a,a):
                yield (a,)+rest


def parity_fibers():
    # Equal first five moments: alternating binomial finite difference of x^d.
    from math import comb
    return tuple(tuple(i+1 for i in range(7) if i%2==parity for _ in range(comb(6,i))) for parity in (0,1))


class Tests(unittest.TestCase):
    def test_partition_counts(self):
        for n,bell in enumerate((1,1,2,5,15,52)):
            p=list(partitions(n))
            self.assertEqual(len(set(p)),bell)
            self.assertEqual(len(p),bell)
    def test_all_integer_partitions(self):
        ncases=0
        for n in range(1,13):
            for f in integer_partitions(n):
                self.assertEqual(counts(f),subset_counts(f),f)
                if n<=7:
                    self.assertEqual(counts(f),oracle(f),f)
                ncases+=1
        self.assertEqual(ncases,271)
    def test_moment_equivalence(self):
        a,b=parity_fibers()
        self.assertNotEqual(a,b)
        self.assertEqual(moments(a),moments(b))
        self.assertNotEqual(sum(r**6 for r in a),sum(r**6 for r in b))
        self.assertEqual(counts(a),subset_counts(a))
        self.assertEqual(counts(b),subset_counts(b))
        self.assertEqual(counts(a),counts(b))
    def test_edge_cases(self):
        for f in [(),(0,),(-1,),(True,),(1.5,)]:
            with self.assertRaises(ValueError): counts(f)
        for f in [(1,)*100,(1000,), (1,2,3,100,1000)*10,(2,)*5]:
            self.assertEqual(counts(f),subset_counts(f))
        self.assertEqual(counts((2,)*5),(68800,11040,6240,13920))


if __name__=='__main__':
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    a,b=parity_fibers()
    print('MOMENT_QUOTIENT_JSON='+json.dumps({'source':'INTERNAL/AI_AUTHORED','partition_cases':271,'moments':moments(a),'equivalent_histogram':counts(a),'sixth_moments':[sum(r**6 for r in f) for f in (a,b)],'limitations':['static aggregate certificate only','not equality of candidate sets','no measured runtime or historical coverage advantage']},sort_keys=True))
