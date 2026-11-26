"""V3.8.10: conditional fixed-size comparator for finite partitions.
INTERNAL/AI_AUTHORED. Descriptive static structure only.

Condition on the response to the other three fixed predicates. Within
each stratum, draw a uniform subset with its observed marginal count.
Independent draws across disjoint strata give additive means and
variances. This preserves between-stratum dependence but deliberately
does not fix counts in each original atom (which would fix the statistic).
"""
from collections import Counter
from fractions import Fraction
from itertools import combinations, product
import json
import unittest
from partition_moments_v3808 import moments, partitions
from unified_static_audit_v3809 import NAMES, metric
from graph_refinement_v3804 import cycle_rank
from local_return_refinement_v3807 import raw_aba
from reciprocal_redundancy_v3806 import local_return


def stratified_moments(strata):
    terms=[moments(sizes,k) for sizes,k in strata]
    mean=sum((t[0] for t in terms),Fraction(0))
    variance=sum((t[2] for t in terms),Fraction(0))
    return mean,mean**2+variance,variance


def conditional_metric(rows,i):
    b=1<<i
    cond=15^b
    groups={}
    for row in rows:
        for s in range(16):
            if s&b:
                continue
            a,c=row[s],row[s|b]
            if a+c:
                groups.setdefault(s,[]).append((a,c))
    strata=[([a+c for a,c in pairs],sum(c for a,c in pairs))
            for _,pairs in sorted(groups.items())]
    observed=sum(a*c for pairs in groups.values() for a,c in pairs)
    mean,_,var=stratified_moments(strata)
    global_result=metric(rows,i,cond)
    assert global_result["separated_pairs"]==observed
    diff=Fraction(observed)-mean
    return {"observed":observed,"stratum_count":len(strata),
            "deterministic_stratum_count":sum(moments(s,k)[2]==0 for s,k in strata),
            "stratified_mean_exact":str(mean),"stratified_variance_exact":str(var),
            "stratified_difference_exact":str(diff),
            "stratified_direction":(diff>0)-(diff<0),
            "global_mean_exact":global_result["fixed_size_mean_exact"],
            "global_variance_exact":global_result["fixed_size_variance_exact"],
            "global_direction":global_result["direction"]}


def audit():
    from signed_order_v3763 import freeze,partition,DOMAIN,digest
    _,raw,_=freeze()
    atoms,counts=partition(raw,DOMAIN)
    width=(DOMAIN+7)//8
    packed=[m.to_bytes(width,"little") for m in raw]
    masks=[bytearray(width) for _ in range(16)]
    direct=Counter()
    for x in range(DOMAIN):
        ds=tuple(map(int,f"{x:05d}"))
        flags=(len(set(ds))<5,cycle_rank(ds)>0,raw_aba(ds),local_return(ds))
        cat=sum(int(v)<<i for i,v in enumerate(flags))
        s=sum(((m[x//8]>>(x%8))&1)<<i for i,m in enumerate(packed))
        direct[s,cat]+=1
        masks[cat][x//8]|=1<<(x%8)
    masks=[int.from_bytes(m,"little") for m in masks]
    rows=[]
    for s,(atom,k) in enumerate(zip(atoms,counts)):
        if k:
            row=[(atom&m).bit_count() for m in masks]
            assert row==[direct[s,j] for j in range(16)]
            assert sum(row)==k
            rows.append(row)
    assert len(rows)==1079
    results={name:conditional_metric(rows,i) for i,name in enumerate(NAMES)}
    return {"schema":"pl5-stratified-comparator-v3810-1","source":"INTERNAL/AI_AUTHORED",
            "domain":DOMAIN,"base_classes":len(rows),
            "rule_mask_sha256":[digest(m) for m in raw],"results":results,
            "limitations":["conditional comparator chosen after prior development audits",
              "uniform independent draws within fixed response strata",
              "not a significance test, not a tail probability",
              "static descriptive comparison only; no historical inputs or operational policy"]}


def brute(strata):
    values=[]
    for sizes,k in strata:
        labels=[i for i,n in enumerate(sizes) for _ in range(n)]
        scores=[]
        for subset in combinations(range(len(labels)),k):
            selected=set(subset)
            scores.append(sum(labels[a]==labels[b] and ((a in selected)!=(b in selected))
                              for a in range(len(labels)) for b in range(a)))
        values.append(scores)
    all_scores=[sum(v) for v in product(*values)]
    mean=Fraction(sum(all_scores),len(all_scores))
    second=Fraction(sum(v*v for v in all_scores),len(all_scores))
    return mean,second,second-mean**2


class Tests(unittest.TestCase):
    def test_direction_reversal(self):
        # Six fixed positives in one stratum; two of four in another.
        strata=[((6,),6),((2,2),2)]
        mean,_,var=stratified_moments(strata)
        self.assertEqual(mean,Fraction(4,3))
        self.assertEqual(var,Fraction(8,9))
        global_mean=moments((6,2,2),8)[0]
        self.assertGreater(global_mean,2)
        self.assertLess(mean,2)
    def test_degenerate(self):
        self.assertEqual(stratified_moments([]),(0,0,0))
        self.assertEqual(stratified_moments([((2,),0),((3,),3)]),(0,0,0))
    def test_exhaustive(self):
        cases=0
        for n in range(1,5):
            for m in range(1,5):
                for a in partitions(n):
                    for b in partitions(m):
                        for k in range(n+1):
                            for l in range(m+1):
                                s=[(a,k),(b,l)]
                                self.assertEqual(stratified_moments(s),brute(s))
                                cases+=1
        self.assertGreater(cases,1000)
    def test_domain(self):
        self.__class__.result=audit()


if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3810_STRATIFIED_JSON="+json.dumps(Tests.result,sort_keys=True))
