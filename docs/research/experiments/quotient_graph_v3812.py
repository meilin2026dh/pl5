"""V3.8.12: static quotient-graph topology audit.
INTERNAL/AI_AUTHORED. Fixed mathematical predicates, no historical inputs.
For a connected transition graph and its simple loop-free quotient,
beta(Q)-beta(G) = (|V|-|V_Q|)-(|E|-|E_Q|).
Neither sign is guaranteed. Positive change implies vertex identification.
"""
from collections import Counter
from itertools import product
from fractions import Fraction
import json
import unittest
from graph_refinement_v3804 import cycle_rank, cycle_dsu, report
from local_return_refinement_v3807 import raw_aba
from reciprocal_redundancy_v3806 import local_return
from curvature_rank_v3811 import curvature
from partition_moments_v3808 import moments


def counts(ds):
    return len(set(ds)),len({tuple(sorted((a,b))) for a,b in zip(ds,ds[1:]) if a!=b})


def predicate(ds):
    q=tuple(d%5 for d in ds)
    before,after=cycle_rank(ds),cycle_rank(q)
    v,e=counts(ds)
    w,f=counts(q)
    assert after-before==(v-w)-(e-f)
    assert before in (0,1) and after in (0,1)
    assert bool(before)==cycle_dsu(ds) and bool(after)==cycle_dsu(q)
    collision=v>w
    assert not after>before or collision
    return before,after,collision


def control(ds):
    # Frozen positional permutation; same marginal cardinality by bijection.
    perm=(ds[0],ds[2],ds[1],ds[3],ds[4])
    return cycle_rank(tuple(d%5 for d in perm))>cycle_rank(perm)


def summarize(rows):
    # Eight categories: quotient gain, position control, vertex collision.
    if any(len(row)!=8 or any(type(k) is not int or k<0 for k in row) for row in rows):
        raise ValueError("invalid contingency")
    def groups(bit,cond):
        out=[]
        for row in rows:
            for s in range(8):
                if s&~cond:
                    continue
                a=sum(k for j,k in enumerate(row) if j&cond==s and not j&bit)
                b=sum(k for j,k in enumerate(row) if j&cond==s and j&bit)
                if a+b:
                    out.append((a,b))
        return out
    def describe(bit,cond):
        g=groups(bit,cond)
        r=report(g,100)
        mean,_,var=moments([a+b for a,b in g],sum(b for a,b in g))
        r["global_fixed_size_mean_exact"]=str(mean)
        r["global_fixed_size_variance_exact"]=str(var)
        r["global_mean_direction"]=(Fraction(r["newly_distinguished_unordered_pairs"])>mean)-(Fraction(r["newly_distinguished_unordered_pairs"])<mean)
        return r
    return {"quotient_gain":describe(1,0),"position_control":describe(2,0),
            "collision_control":describe(4,0),
            "gain_given_collision":describe(1,4),
            "gain_given_position_and_collision":describe(1,6),
            "position_given_gain_and_collision":describe(2,5),
            "category_sizes":[sum(row[j] for row in rows) for j in range(8)]}


def audit():
    from signed_order_v3763 import freeze,partition,DOMAIN,digest
    _,raw,_=freeze()
    atoms,ks=partition(raw,DOMAIN)
    width=(DOMAIN+7)//8
    original=[m.to_bytes(width,"little") for m in raw]
    packed={}
    direct=Counter()
    transition=Counter()
    for x in range(DOMAIN):
        ds=tuple(map(int,f"{x:05d}"))
        b,c,collision=predicate(ds)
        transition[b,c]+=1
        cat=int(c>b)+2*int(control(ds))+4*int(collision)
        flags=(len(set(ds))<5,b>0,raw_aba(ds),local_return(ds),*curvature(ds))
        base=sum(int(v)<<j for j,v in enumerate(flags))
        key=base,cat
        if key not in packed:
            packed[key]=bytearray(width)
        packed[key][x//8]|=1<<(x%8)
        s=sum(((m[x//8]>>(x%8))&1)<<j for j,m in enumerate(original))
        direct[s,base,cat]+=1
    packed={k:int.from_bytes(m,"little") for k,m in packed.items()}
    bases=sorted({base for base,cat in packed})
    rows=[]
    for s,(atom,k) in enumerate(zip(atoms,ks)):
        if not k:
            continue
        block=[]
        for base in bases:
            row=tuple((atom&packed.get((base,cat),0)).bit_count() for cat in range(8))
            assert row==tuple(direct[s,base,cat] for cat in range(8))
            if sum(row):
                block.append(row)
        assert sum(map(sum,block))==k
        rows.extend(block)
    assert len(rows)==8879
    assert transition=={(0,0):68800,(0,1):11040,(1,0):6240,(1,1):13920}
    result=summarize(rows)
    assert result["quotient_gain"]["positive_mask_size"]==result["position_control"]["positive_mask_size"]==11040
    assert result["collision_control"]["positive_mask_size"]==63750
    return {"schema":"pl5-quotient-graph-v3812-1","source":"INTERNAL/AI_AUTHORED",
            "domain":DOMAIN,"baseline_coordinate_count":18,"base_classes":len(rows),
            "rule_mask_sha256":[digest(m) for m in raw],
            "transitions":{f"{a}->{b}":k for (a,b),k in sorted(transition.items())},
            "result":result,"limitations":["static aggregate refinement only",
              "fixed 12-rule baseline plus six experimental predicates, not full inventory",
              "position permutation is a matched-marginal structural control, not matched cost",
              "collision control not equal-sized; global comparator does not preserve dependencies",
              "capped-class union is not one capped candidate set",
              "no historical inputs, operational selection, or mathematical novelty claim"]}


class Tests(unittest.TestCase):
    def test_examples(self):
        self.assertEqual(predicate((0,1,2,5,5))[:2],(0,1))
        self.assertEqual(predicate((0,1,5,0,0))[:2],(1,0))
        self.assertEqual(predicate((0,1,2,0,0))[:2],(1,1))
    def test_exhaustive_small(self):
        for ds in product((0,1,2,5,6),repeat=5):
            self.assertEqual(predicate(ds),predicate(ds[::-1]))
    def test_toy_conditional(self):
        r=summarize([(2,0,0,0,3,4,0,0)])
        self.assertEqual(r["quotient_gain"]["newly_distinguished_unordered_pairs"],20)
        self.assertEqual(r["gain_given_collision"]["newly_distinguished_unordered_pairs"],12)
    def test_domain(self):
        self.__class__.result=audit()


if __name__=="__main__":
    if not unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful():
        raise SystemExit(1)
    print("V3812_QUOTIENT_GRAPH_JSON="+json.dumps(Tests.result,sort_keys=True))
