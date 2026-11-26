"""V3.8.3 regression gate: exact partition equivalence with a witness.
INTERNAL/AI_AUTHORED. Synthetic finite sets only; no production behavior.
"""
from itertools import combinations, product
from collections import Counter
import json
import unittest


def refinement_witness(a, b):
    """Return indices i,j with a[i]==a[j] and b[i]!=b[j], or None.

    Equal-length nonempty sequences of hashable labels are required.
    A single pass uses O(n) expected time and O(number of A classes) space.
    """
    if len(a) != len(b) or not len(a):
        raise ValueError("partitions must share a nonempty indexed domain")
    first = {}
    for j, (x, y) in enumerate(zip(a, b)):
        if x in first:
            i, old = first[x]
            if old != y:
                return i, j
        else:
            first[x] = (j, y)
    return None


def equivalent(a, b):
    return refinement_witness(a, b) is None and refinement_witness(b, a) is None


def partitions(n):
    # Independent brute-force canonical label generator, not recursive growth.
    return [a for a in product(range(n), repeat=n)
            if a[0] == 0 and all(a[i] <= 1 + max(a[:i]) for i in range(1, n))]


class Tests(unittest.TestCase):
    def test_counterexample(self):
        a, b = (0, 0, 1), (0, 1, 0)
        self.assertFalse(equivalent(a, b))
        self.assertEqual(refinement_witness(a, b), (0, 1))
        self.assertEqual(refinement_witness(b, a), (0, 2))
        self.assertTrue(equivalent(a, ('a', 'a', 'b')))

    def test_domain_validation(self):
        for a, b in [((), ()), ((1,), (1, 2))]:
            with self.assertRaises(ValueError):
                equivalent(a, b)

    def test_exhaustive(self):
        expected = [(1, 0, 0, 0), (2, 0, 0, 2), (5, 6, 6, 14),
                    (15, 72, 48, 90), (52, 900, 500, 612),
                    (203, 13310, 6860, 4536)]
        rows = []
        for n, target in enumerate(expected, 1):
            p = partitions(n)
            meta = [(a, frozenset((i,j) for i,j in combinations(range(n),2)
                                  if a[i] == a[j]), len(set(a)),
                     sorted(Counter(a).values())) for a in p]
            sc = sh = sr = 0
            for a, ra, ca, ha in meta:
                for b, rb, cb, hb in meta:
                    w = refinement_witness(a, b)
                    v = refinement_witness(b, a)
                    self.assertEqual(w is None, ra <= rb)
                    self.assertEqual(v is None, rb <= ra)
                    for witness, x, y in ((w,a,b),(v,b,a)):
                        if witness is not None:
                            i,j = witness
                            self.assertTrue(i < j and x[i] == x[j] and y[i] != y[j])
                    eq = w is None and v is None
                    self.assertEqual(eq, len(set(zip(a,b))) == ca == cb)
                    if not eq:
                        sc += ca == cb
                        sh += ha == hb
                        sr += w is None or v is None
            self.assertEqual((len(p), sc, sh, sr), target)
            rows.append(dict(n=n, partitions=len(p), pairs=len(p)**2,
                             same_count_false=sc, same_histogram_false=sh,
                             strict_refinement=sr))
        self.assertEqual(sum(r['pairs'] for r in rows), 44168)
        Tests.rows = rows

    def test_large_synthetic_relabel(self):
        a = [i % 1079 for i in range(100000)]
        b = [str(x) for x in a]
        self.assertTrue(equivalent(a, b))
        b[-1] = 'new'
        self.assertFalse(equivalent(a, b))
        self.assertIsNotNone(refinement_witness(a, b))
        self.assertIsNone(refinement_witness(b, a))


if __name__ == '__main__':
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print('V3803_PARTITION_EQUIVALENCE_JSON=' + json.dumps(
        dict(source='INTERNAL/AI_AUTHORED', rows=Tests.rows,
             limitations='synthetic validation only; no compression or timing claim'),
        sort_keys=True))
