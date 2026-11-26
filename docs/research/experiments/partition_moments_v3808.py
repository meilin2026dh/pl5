"""V3.8.8: exact moment audit for the fixed-size random partition comparator.
INTERNAL/AI_AUTHORED. Abstract finite partitions and synthetic tests only.

Let X count within-class unordered pairs separated by a uniformly sampled
k-subset of N elements. Let M=sum C(n_i,2), A=3 sum C(n_i,3) and
B=C(M,2)-A. Two distinct within-class pairs either share one vertex (A)
or have four distinct vertices (B).

For a single pair, p=2*k*(N-k)/(N*(N-1)).
For two overlapping pairs both to be separated, the shared vertex must
have the opposite membership from both others, giving q=p/2.
For two disjoint pairs both to be separated, exactly one vertex from
each pair must be selected, giving r=4*(k)_2*(N-k)_2/(N)_4.
Terms with impossible vertex configurations are zero.

By expanding X as a sum of pair indicators:
 E[X]=M*p, E[X^2]=M*p+2*A*q+2*B*r.
 Variance=E[X^2]-E[X]^2.

The exact mean alone is not a significance test, and the variance alone
does not determine a tail probability. No observed data or rule search.
"""
from fractions import Fraction
from itertools import combinations
from math import comb
import json
import unittest


def moments(sizes, k):
    sizes=tuple(sizes)
    if any(type(n) is not int or n<=0 for n in sizes):
        raise ValueError("class sizes must be positive integers")
    N=sum(sizes)
    if type(k) is not int or not 0<=k<=N:
        raise ValueError("invalid subset size")
    M=sum(comb(n,2) for n in sizes)
    A=3*sum(comb(n,3) for n in sizes)
    B=comb(M,2)-A
    p=Fraction(2*k*(N-k),N*(N-1)) if N>=2 else Fraction(0)
    q=p/2 if N>=3 else Fraction(0)
    r=Fraction(4*k*(k-1)*(N-k)*(N-k-1),N*(N-1)*(N-2)*(N-3)) if N>=4 else Fraction(0)
    mean=M*p
    second=M*p+2*A*q+2*B*r
    variance=second-mean**2
    assert B>=0 and variance>=0
    return mean,second,variance


def partitions(n, minimum=1):
    if n==0:
        yield ()
    for i in range(minimum,n+1):
        for tail in partitions(n-i,i):
            yield (i,)+tail


def oracle(sizes,k):
    labels=[i for i,n in enumerate(sizes) for _ in range(n)]
    N=len(labels)
    count=s1=s2=0
    for subset in combinations(range(N),k):
        selected=set(subset)
        x=sum(labels[a]==labels[b] and ((a in selected)!=(b in selected))
              for a in range(N) for b in range(a))
        count+=1
        s1+=x
        s2+=x*x
    mean=Fraction(s1,count)
    second=Fraction(s2,count)
    return (mean,second,second-mean**2),count


class Tests(unittest.TestCase):
    def test_empty_and_degenerate(self):
        for sizes,k in [((),0),((1,),0),((1,),1),((1,1,1),2),((2,3),0),((2,3),5)]:
            self.assertEqual(moments(sizes,k),(0,0,0))
        self.assertEqual(moments((4,),2),(4,16,0))

    def test_equal_mean_different_variance(self):
        # Same N=6 and M=3, different shared-vertex configuration.
        a=moments((3,1,1,1),2)
        b=moments((2,2,2),2)
        self.assertEqual(a[0],b[0])
        self.assertNotEqual(a[2],b[2])

    def test_invalid(self):
        for sizes,k in [((0,),0),((-1,),0),((2,),3),((2,),-1),((2.0,),1)]:
            with self.assertRaises(ValueError):
                moments(sizes,k)

    def test_exhaustive(self):
        cases=total=0
        for N in range(1,10):
            for sizes in partitions(N):
                for k in range(N+1):
                    expected,count=oracle(sizes,k)
                    self.assertEqual(moments(sizes,k),expected,(sizes,k))
                    self.assertEqual(moments(sizes,N-k),expected)
                    total+=count
                    cases+=1
        self.assertEqual((cases,total),(782,23954))
        self.__class__.result={"schema":"finite-partition-moment-audit-v3808-1",
            "source":"INTERNAL/AI_AUTHORED","max_synthetic_domain":9,
            "partition_budget_cases":cases,"enumerated_subsets":total,
            "limitations":["synthetic exact moment identity only",
            "not a tail probability or empirical significance test",
            "no measured cost or historical coverage result"]}


if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3808_MOMENT_JSON="+json.dumps(Tests.result,sort_keys=True))
