"""INTERNAL/AI_AUTHORED: exact implication classification, five-symbol words.

For a partition P, R_P is the binary simple quotient-cycle predicate.
Partitions with fewer than three blocks yield the empty positive set.
For distinct partitions with at least three blocks, neither R_P implies
R_Q nor R_Q implies R_P. This certifies pairwise non-redundancy, not
independence from a portfolio or any historical coverage improvement.

Proof: if a,b share a Q block but not a P block, choose c in a third P
block. (a,b,c,a,a) is a triangle under P but not Q. In the incomparable
case apply this argument in both directions. If P strictly refines Q,
choose a,b in distinct P blocks of the same Q block and c,d in two other
Q blocks. (a,c,d,b,b) is a simple path under P and a triangle under Q.
The opposite witness is (a,b,c,a,a). These cover all distinct partitions.
"""
from itertools import combinations, product
import json
import unittest


def partitions(n):
    if n == 0:
        yield ()
    else:
        for p in partitions(n-1):
            for k in range(max(p, default=-1)+2):
                yield p+(k,)


def positive(p, w):
    labels=tuple(p[x] for x in w)
    edges={tuple(sorted((a,b))) for a,b in zip(labels,labels[1:]) if a!=b}
    return len(edges)>=len(set(labels))


def witness(p,q):
    """Construct R_p=True, R_q=False; None iff implication holds."""
    if len(set(p))<3 or p==q:
        return None
    for a,b in combinations(range(len(p)),2):
        if p[a]!=p[b] and q[a]==q[b]:
            c=next(i for i in range(len(p)) if p[i] not in (p[a],p[b]))
            return a,b,c,a,a
    # q refines p (with equality excluded). Choose a split p block.
    for a,b in combinations(range(len(p)),2):
        if p[a]==p[b] and q[a]!=q[b]:
            c=next(i for i in range(len(p)) if p[i]!=p[a])
            d=next(i for i in range(len(p)) if p[i] not in (p[a],p[c]))
            return a,c,d,b,b
    raise AssertionError('canonical distinct partitions must differ')


def audit():
    totals={}
    for n in range(1,6):
        ps=list(partitions(n))
        masks=[]
        # Independent word oracle: count a triangle or a simple four-cycle.
        for p in ps:
            mask=0
            for i,w in enumerate(product(range(n),repeat=5)):
                s=tuple(p[x] for x in w)
                e={frozenset((a,b)) for a,b in zip(s,s[1:]) if a!=b}
                cyc=any(all(frozenset((a,b)) in e for a,b in zip(t,t[1:]+t[:1]))
                        for k in (3,4) for t in __import__('itertools').permutations(set(s),k))
                if cyc:
                    mask|=1<<i
            masks.append(mask)
        nonempty=sum(bool(m) for m in masks)
        checked=0
        for i,p in enumerate(ps):
            for j,q in enumerate(ps):
                w=witness(p,q)
                actual=bool(masks[i]&~masks[j])
                assert (w is not None)==actual,(p,q)
                if w is not None:
                    assert positive(p,w) and not positive(q,w),(p,q,w)
                assert actual==(len(set(p))>=3 and p!=q)
                checked+=1
        totals[n]={'partitions':len(ps),'nonempty':nonempty,'ordered_pairs':checked}
    return totals


class Tests(unittest.TestCase):
    def test_exhaustive(self):
        self.__class__.result=audit()
        self.assertEqual(self.result[5],{'partitions':52,'nonempty':36,'ordered_pairs':2704})

    def test_decimal_witnesses(self):
        p=tuple(range(10))
        q=(0,0,1,2,3,4,5,6,7,8)
        for a,b in ((p,q),(q,p)):
            w=witness(a,b)
            self.assertTrue(positive(a,w))
            self.assertFalse(positive(b,w))
        self.assertIsNone(witness((0,)*10,p))


if __name__=='__main__':
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print(json.dumps({'source':'INTERNAL/AI_AUTHORED','audit':Tests.result,
                      'limitations':['static pairwise implication only','not portfolio independence','no historical coverage or runtime claim']},sort_keys=True))
