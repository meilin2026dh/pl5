"""V3.7.73: full subset entropy and Shapley audit of frozen rules.
INTERNAL/AI_AUTHORED. Uniform finite-domain descriptive statistics only.
No historical records, new rules, or candidate-selection policies.
"""
from collections import Counter
from math import log2, fsum, comb, isclose
import json
import unittest
from signed_order_v3763 import freeze, partition, DOMAIN, digest

TOL = 1e-10


def subset_entropies(counts, n):
    if not 1 <= n <= 12 or len(counts) != 1 << n:
        raise ValueError("invalid bounded inventory")
    total = sum(counts)
    if total <= 0 or any(k < 0 for k in counts):
        raise ValueError("invalid counts")
    # Project full Boolean atoms onto each subset of coordinates.
    occupied = [(s,k) for s,k in enumerate(counts) if k]
    out = []
    for subset in range(1 << n):
        groups = Counter()
        for signature,k in occupied:
            groups[signature & subset] += k
        assert sum(groups.values()) == total
        out.append(fsum(-k/total*log2(k/total) for k in sorted(groups.values())))
    return out


def decompose(h, n):
    full = (1 << n)-1
    values = []
    violations = 0
    largest_conditional_mi = 0.0
    smallest_conditional_mi = 0.0
    for j in range(n):
        bit = 1 << j
        terms = []
        for s in range(1 << n):
            if s & bit:
                continue
            delta = h[s|bit]-h[s]
            assert delta >= -TOL
            terms.append(delta/(n*comb(n-1,s.bit_count())))
            for i in range(j+1,n):
                b = 1 << i
                if s & b:
                    continue
                # Conditional mutual information, never negative in exact arithmetic.
                cmi = delta-(h[s|b|bit]-h[s|b])
                violations += cmi < -TOL
                largest_conditional_mi = max(largest_conditional_mi,cmi)
                smallest_conditional_mi = min(smallest_conditional_mi,cmi)
        values.append({"singleton_bits":h[bit],
                       "leave_one_out_bits":h[full]-h[full^bit],
                       "shapley_bits":fsum(terms)})
    assert violations == 0
    assert isclose(fsum(v["shapley_bits"] for v in values),h[full],abs_tol=TOL)
    return values, {"submodularity_violations":violations,
                    "largest_conditional_mi_bits":largest_conditional_mi,
                    "smallest_conditional_mi_bits":smallest_conditional_mi}


def audit(raw, size, names):
    n = len(raw)
    _,counts = partition(raw,size)
    h = subset_entropies(counts,n)
    values, checks = decompose(h,n)
    pairs = [{"i":names[i],"j":names[j],
              "mutual_information_bits":h[1<<i]+h[1<<j]-h[(1<<i)|(1<<j)]}
             for i in range(n) for j in range(i+1,n)]
    # Static descriptive comparisons: total correlation, not a causal synergy measure.
    joint = h[-1]
    return {"schema":"pl5-static-entropy-v3773-1","source":"INTERNAL/AI_AUTHORED",
            "domain":size,"subset_count":len(h),"joint_entropy_bits":joint,
            "total_correlation_bits":fsum(h[1<<j] for j in range(n))-joint,
            "rules":[dict(name=name,**v) for name,v in zip(names,values)],
            "pairwise_mutual_information":pairs,"checks":checks,
            "rule_mask_sha256":[digest(m) for m in raw],
            "limitations":["uniform finite domain, not empirical temporal distribution",
                "entropy is monotone submodular, not evidence of superadditive synergy",
                "Shapley allocation depends on frozen inventory and objective",
                "floating point tolerance 1e-10; no historical coverage or search policy"]}


class Tests(unittest.TestCase):
    def test_independent_and_duplicate(self):
        h = subset_entropies([1,1,1,1],2)
        self.assertEqual(h,[0,1,1,2])
        v,_ = decompose(h,2)
        self.assertEqual([x["shapley_bits"] for x in v],[1,1])
        h = subset_entropies([2,0,0,2],2)
        v,_ = decompose(h,2)
        self.assertEqual([x["shapley_bits"] for x in v],[.5,.5])
        self.assertEqual([x["leave_one_out_bits"] for x in v],[0,0])
    def test_xor_and_constant(self):
        h = subset_entropies([1,0,0,1,0,1,1,0],3)
        v,checks = decompose(h,3)
        self.assertAlmostEqual(h[-1],2)
        for x in v:
            self.assertAlmostEqual(x["shapley_bits"],2/3)
            self.assertAlmostEqual(x["leave_one_out_bits"],0)
        self.assertAlmostEqual(checks["largest_conditional_mi_bits"],1)
        h = subset_entropies([1,1,0,0],2)
        v,_ = decompose(h,2)
        self.assertEqual(v[1]["shapley_bits"],0)
    def test_independent_direct_projection(self):
        raw = (3,6,5,3)
        _,counts = partition(raw,3)
        h = subset_entropies(counts,len(raw))
        for s in range(len(h)):
            groups = Counter(tuple((raw[j]>>x)&1 for j in range(len(raw)) if s>>j&1)
                             for x in range(3))
            self.assertAlmostEqual(h[s],log2(3)-fsum(k*log2(k) for k in groups.values())/3)
    def test_frozen(self):
        names,raw,_ = freeze()
        r = audit(raw,DOMAIN,names)
        self.assertEqual(r["subset_count"],4096)
        self.assertEqual(r["checks"]["submodularity_violations"],0)
        self.__class__.result = r


if __name__ == "__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3773_ENTROPY_JSON="+json.dumps(Tests.result,sort_keys=True))
