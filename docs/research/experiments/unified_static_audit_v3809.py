"""V3.8.9: unified static pair-distinction audit of four fixed predicates.
INTERNAL/AI_AUTHORED. Descriptive aggregate structure, no historical inputs.
"""
from collections import Counter
from fractions import Fraction
from itertools import combinations, product
from math import comb
import json
import unittest

from graph_refinement_v3804 import cycle_rank, cycle_dsu
from reciprocal_redundancy_v3806 import local_return, reciprocal
from local_return_refinement_v3807 import raw_aba
from partition_moments_v3808 import moments

NAMES=("repeat","cycle","direct_ABA","collapsed_return")


def metric(rows, coordinate, conditioning):
    bit=1<<coordinate
    if bit&conditioning:
        raise ValueError("target must not be conditioned on itself")
    groups=[]
    for row in rows:
        counts=Counter()
        for j,k in enumerate(row):
            if k:
                counts[j&conditioning, int(bool(j&bit))]+=k
        for s in sorted({s for s,t in counts}):
            groups.append((counts[s,0],counts[s,1]))
    sizes=[a+b for a,b in groups]
    k=sum(b for a,b in groups)
    observed=sum(a*b for a,b in groups)
    mean,second,var=moments(sizes,k)
    diff=Fraction(observed)-mean
    return {"classes_before":len(groups),
            "split_classes":sum(a>0 and b>0 for a,b in groups),
            "separated_pairs":observed,
            "positive_count":k,
            "fixed_size_mean_exact":str(mean),
            "fixed_size_variance_exact":str(var),
            "difference_from_mean_exact":str(diff),
            "direction":(diff>0)-(diff<0),
            "ratio_to_mean_exact":str(observed/mean) if mean else None,
            "squared_standardized_difference_exact":str(diff**2/var) if var else None,
            "zero_variance":var==0}


def analyze(rows):
    if any(len(row)!=16 or any(type(k) is not int or k<0 for k in row) for row in rows):
        raise ValueError("expected nonnegative integer four-bit contingency rows")
    stats={}
    joint=0
    overlap=[[0]*4 for _ in range(4)]
    multiplicity=[0]*5
    for row in rows:
        multiplicity[0]+=sum(comb(k,2) for k in row)
        for a,b in combinations(range(16),2):
            w=row[a]*row[b]
            difference=a^b
            multiplicity[difference.bit_count()]+=w
            joint+=w
            for i in range(4):
                if difference>>i&1:
                    for j in range(4):
                        if difference>>j&1:
                            overlap[i][j]+=w
    for i,name in enumerate(NAMES):
        alone=metric(rows,i,0)
        conditional=metric(rows,i,15^(1<<i))
        assert alone["separated_pairs"]==overlap[i][i]
        assert conditional["separated_pairs"]<=alone["separated_pairs"]
        stats[name]={"standalone":alone,"given_other_three":conditional}
    assert sum(x["given_other_three"]["separated_pairs"] for x in stats.values())==multiplicity[1]
    assert joint==sum(multiplicity[1:])
    assert sum(multiplicity)==sum(comb(sum(row),2) for row in rows)
    return {"rules":stats,"joint_distinguished_pairs":joint,
            "pairwise_overlap_matrix":overlap,"distinction_multiplicity":multiplicity}


def audit():
    from signed_order_v3763 import freeze,partition,DOMAIN,digest
    _,raw,_=freeze()
    atoms,counts=partition(raw,DOMAIN)
    width=(DOMAIN+7)//8
    original=[m.to_bytes(width,"little") for m in raw]
    masks=[bytearray(width) for _ in range(16)]
    direct=Counter()
    for x in range(DOMAIN):
        ds=tuple(map(int,f"{x:05d}"))
        flags=(len(set(ds))<5,cycle_rank(ds)>0,raw_aba(ds),local_return(ds))
        assert flags[1]==cycle_dsu(ds) and flags[3]==reciprocal(ds)
        assert not flags[1] or flags[0]
        assert not flags[2] or flags[3]
        category=sum(int(v)<<j for j,v in enumerate(flags))
        masks[category][x//8]|=1<<(x%8)
        signature=sum(((m[x//8]>>(x%8))&1)<<j for j,m in enumerate(original))
        direct[signature,category]+=1
    packed=[int.from_bytes(m,"little") for m in masks]
    rows=[]
    for s,(atom,k) in enumerate(zip(atoms,counts)):
        if k:
            row=[(atom&m).bit_count() for m in packed]
            assert row==[direct[s,j] for j in range(16)]
            assert sum(row)==k
            rows.append(row)
    assert len(rows)==1079
    result=analyze(rows)
    assert result["rules"]["repeat"]["standalone"]["separated_pairs"]==25666025
    assert result["rules"]["cycle"]["standalone"]["separated_pairs"]==19478110
    assert result["rules"]["collapsed_return"]["standalone"]["positive_count"]==26190
    return {"schema":"pl5-unified-static-audit-v3809-1","source":"INTERNAL/AI_AUTHORED",
            "domain":DOMAIN,"base_classes":len(rows),"rule_names":NAMES,
            "rule_mask_sha256":[digest(m) for m in raw],"result":result,
            "limitations":["fixed static inventory; retrospective descriptive comparison",
              "global uniform fixed-size comparator ignores dependencies on conditioning predicates",
              "squared standardized difference is descriptive, not a p-value or normal approximation",
              "no multiple-testing inference, no operational selection, no historical coverage",
              "no measured computation cost or full-inventory nonredundancy claim"]}


class Tests(unittest.TestCase):
    def test_duplicate_predicates(self):
        row=[0]*16
        row[0]=2
        row[15]=3
        r=analyze([row])
        self.assertEqual(r["joint_distinguished_pairs"],6)
        for x in r["rules"].values():
            self.assertEqual(x["standalone"]["separated_pairs"],6)
            self.assertEqual(x["given_other_three"]["separated_pairs"],0)
        self.assertEqual(r["distinction_multiplicity"],[4,0,0,0,6])

    def test_distinct_pairs(self):
        row=[0]*16
        for s in (0,1,2,4,8):
            row[s]=1
        r=analyze([row])
        self.assertEqual(r["joint_distinguished_pairs"],10)
        self.assertEqual(r["distinction_multiplicity"],[0,4,6,0,0])
        for x in r["rules"].values():
            self.assertEqual(x["given_other_three"]["separated_pairs"],1)

    def test_expanded_oracle(self):
        for seq in product((0,1,3,15),repeat=4):
            row=[seq.count(j) for j in range(16)]
            r=analyze([row])
            for i,name in enumerate(NAMES):
                bit=1<<i
                expected=sum((a^b)==bit for a,b in combinations(seq,2))
                self.assertEqual(r["rules"][name]["given_other_three"]["separated_pairs"],expected)

    def test_degenerate(self):
        self.assertTrue(metric([[1]+[0]*15],0,0)["zero_variance"])
        with self.assertRaises(ValueError):
            analyze([[1,2]])

    def test_domain(self):
        self.__class__.result=audit()


if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3809_UNIFIED_JSON="+json.dumps(Tests.result,sort_keys=True))
