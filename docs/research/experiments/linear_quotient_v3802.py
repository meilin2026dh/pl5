"""V3.8.2: exact codimension-one GF(2) expression audit.
INTERNAL/AI_AUTHORED. Frozen static rule responses only; no historical inputs.

For a nonempty realized signature set R in GF(2)^n, any rank n-1
linear map has kernel {0,d}, d != 0. It is injective on R iff
no distinct x,y in R satisfy x XOR y = d. The number of merged
pairs is exactly the unordered difference count at d, because
each coset contains at most two signatures. Every nonzero d is
a possible one-dimensional kernel. Thus exhaustive difference
counts determine feasibility without enumerating linear matrices.
An affine translation cannot change these collision counts.
Only aggregate evidence is emitted, not a filtering policy.
"""
from collections import Counter
import json
import unittest


def fwht(values):
    """Unnormalized exact integer Walsh-Hadamard transform."""
    out = list(values)
    step = 1
    while step < len(out):
        for base in range(0, len(out), 2*step):
            for i in range(base, base+step):
                a, b = out[i], out[i+step]
                out[i], out[i+step] = a+b, a-b
        step *= 2
    return out


def audit_signatures(rows, n):
    if type(n) is not int or not 1 <= n <= 12:
        raise ValueError("bounded signature width required")
    rows = sorted(set(rows))
    size = 1 << n
    if not rows or rows[0] < 0 or rows[-1] >= size:
        raise ValueError("nonempty valid signatures required")
    # Oracle A: exhaustive unordered pairs.
    direct = [0]*size
    for i, x in enumerate(rows):
        for y in rows[:i]:
            direct[x ^ y] += 1
    # Oracle B: XOR autocorrelation of the support indicator.
    support = [0]*size
    for x in rows:
        support[x] = 1
    transformed = fwht(support)
    corr = fwht([v*v for v in transformed])
    assert corr[0] == size*len(rows)
    assert all(c % (2*size) == 0 for c in corr[1:])
    assert direct[1:] == [c//(2*size) for c in corr[1:]]
    # Oracle C: independently group each possible kernel coset.
    for d in range(1, size):
        projected_count = len({min(x, x ^ d) for x in rows})
        assert len(rows)-projected_count == direct[d]
    assert sum(direct) == len(rows)*(len(rows)-1)//2
    missing = sum(v == 0 for v in direct[1:])
    return {
        "signature_width":n,
        "occupied_classes":len(rows),
        "tested_nonzero_kernels":size-1,
        "collision_free_kernel_count":missing,
        "colliding_kernel_count":size-1-missing,
        "unordered_class_pairs":sum(direct),
        "max_class_merges":max(direct[1:]),
        "collision_histogram":dict(sorted(Counter(direct[1:]).items())),
        "codimension_one_linear_encoding_exists":missing > 0,
    }


def audit():
    from signed_order_v3763 import freeze, partition, DOMAIN, digest
    _, raw, _ = freeze()
    _, counts = partition(raw, DOMAIN)
    result = audit_signatures([s for s,k in enumerate(counts) if k],len(raw))
    return {"schema":"pl5-linear-quotient-v3802-1",
            "source":"INTERNAL/AI_AUTHORED","domain":DOMAIN,
            "rule_mask_sha256":[digest(m) for m in raw],
            "result":result,
            "limitations":["frozen twelve-coordinate inventory only",
                "class collision counts are not identity-weighted",
                "encoding feasibility is not a lower evaluation cost",
                "no new filtering rule or historical coverage measurement"]}


class Tests(unittest.TestCase):
    def test_complete_cube(self):
        r = audit_signatures(range(8),3)
        self.assertEqual(r["collision_free_kernel_count"],0)
        self.assertEqual(r["collision_histogram"],{4:7})

    def test_sparse_and_singleton(self):
        r = audit_signatures([0,1,2],3)
        self.assertEqual(r["collision_histogram"],{0:4,1:3})
        self.assertEqual(audit_signatures([7],3)["collision_free_kernel_count"],7)

    def test_exhaustive_small(self):
        for mask in range(1,256):
            rows = [r for r in range(8) if mask>>r&1]
            r = audit_signatures(rows,3)
            self.assertEqual(r["tested_nonzero_kernels"],7)
            self.assertEqual(sum(r["collision_histogram"].values()),7)
            self.assertEqual(r["unordered_class_pairs"],len(rows)*(len(rows)-1)//2)

    def test_invalid(self):
        for rows,n in (([],3),([8],3),([-1],3),([0],13)):
            with self.assertRaises(ValueError):
                audit_signatures(rows,n)

    def test_frozen(self):
        r = audit()
        expected = r["result"]
        # Independently reconstructed static inventory, with all twelve
        # mask digests matching V3.8.1; aggregate findings only.
        self.assertEqual(expected["occupied_classes"],1079)
        self.assertEqual(expected["tested_nonzero_kernels"],4095)
        self.assertEqual(expected["collision_free_kernel_count"],116)
        self.assertEqual(expected["colliding_kernel_count"],3979)
        self.assertEqual(expected["unordered_class_pairs"],581581)
        self.assertEqual(expected["max_class_merges"],499)
        self.__class__.result = r


if __name__ == "__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3802_LINEAR_QUOTIENT_JSON="+json.dumps(Tests.result,sort_keys=True))
