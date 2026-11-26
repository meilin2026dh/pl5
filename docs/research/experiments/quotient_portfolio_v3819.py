"""INTERNAL/AI_AUTHORED: union implication for elementary coarsenings.

Abstract length-five words on n distinct symbols. R is the simple graph
cycle predicate and R_e identifies the two symbols of one unordered pair e.
For a positive word, the set of e that destroy its cycle is either the three
edges of its triangle (possibly with a tail), or the two diagonals of its
four-cycle. Identification of any other pair preserves a cycle. Conversely
any triangle or two disjoint pairs can be realized by a padded triangle walk
or a four-cycle walk. Therefore R is contained in the union of R_e for a
portfolio E iff E is not a subset of any such obstruction. Empty portfolios
are included in the obstruction test for n>=3. For n<3 R is empty.
This applies only to elementary coarsenings of the identity partition.
"""
from itertools import combinations, product
import json
import unittest


def obstructions(n):
    edges = list(combinations(range(n), 2))
    index = {e: i for i, e in enumerate(edges)}
    masks = set()
    for t in combinations(range(n), 3):
        masks.add(sum(1 << index[e] for e in combinations(t, 2)))
    for i, e in enumerate(edges):
        for j in range(i):
            if len(set(e + edges[j])) == 4:
                masks.add((1 << i) | (1 << j))
    return edges, masks


def contains_identity(n, portfolio):
    edges, masks = obstructions(n)
    if type(portfolio) is not int or not 0 <= portfolio < 1 << len(edges):
        raise ValueError('invalid portfolio mask')
    return not any(portfolio & ~m == 0 for m in masks)


def positive(w):
    edges = {frozenset((a, b)) for a, b in zip(w, w[1:]) if a != b}
    return len(edges) >= len(set(w))


def oracle(n):
    edges = list(combinations(range(n), 2))
    observed = set()
    for w in product(range(n), repeat=5):
        if positive(w):
            failure = 0
            for i, (a, b) in enumerate(edges):
                if not positive(tuple(a if x == b else x for x in w)):
                    failure |= 1 << i
            observed.add(failure)
    return observed


def audit():
    results = {}
    for n in range(1, 7):
        edges, predicted = obstructions(n)
        actual = oracle(n)
        assert actual == predicted, (n, actual, predicted)
        covering = 0
        for p in range(1 << len(edges)):
            formula = not any(p & ~m == 0 for m in predicted)
            direct = not any(p & ~m == 0 for m in actual)
            assert formula == direct
            covering += formula
        results[n] = {'portfolios': 1 << len(edges), 'obstructions': len(actual), 'covering': covering}
    return results


class Tests(unittest.TestCase):
    def test_exhaustive(self):
        self.__class__.result = audit()

    def test_minimal_collective(self):
        edges, _ = obstructions(6)
        p = sum(1 << edges.index(e) for e in ((0, 1), (2, 3), (4, 5)))
        self.assertTrue(contains_identity(6, p))
        for i in range(len(edges)):
            if p & (1 << i):
                self.assertFalse(contains_identity(6, p ^ (1 << i)))
        # Two edges never suffice: they share a triangle or are disjoint.
        for i, j in combinations(range(len(edges)), 2):
            self.assertFalse(contains_identity(6, (1 << i) | (1 << j)))

    def test_invalid(self):
        for p in (-1, True, 8):
            with self.assertRaises(ValueError):
                contains_identity(3, p)


if __name__ == '__main__':
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print(json.dumps({'source': 'INTERNAL/AI_AUTHORED', 'audit': Tests.result,
                      'limitations': ['abstract static union implication only', 'elementary coarsenings only', 'no historical coverage or measured cost claim']}, sort_keys=True))
