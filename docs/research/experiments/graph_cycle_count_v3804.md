# V3.8.4 graph-cycle combinatorial count certificate

Source: INTERNAL/AI_AUTHORED. Static structural audit only. Definition fixed by graph_refinement_v3804.py at 829fcf4412a364b9ac4b189f9b16401e7ca36035.

Canonicalize five-symbol sequences by numbering distinct symbols in first-appearance order. The resulting restricted-growth words are in bijection with the 52 partitions of five positions. Each word with k distinct labels has (q)_k realizations on an alphabet of size q. The simple undirected transition graph is connected and invariant under relabeling. Checking the 52 words yields ten cyclic words, seven with k=3 and three with k=4, each with cycle rank one. Thus the cyclic count is 7(q)_3+3(q)_4=q(q-1)(q-2)(3q-2) for nonnegative integer q. No other cycle rank occurs for five positions.

A separate local Python exhaustive enumeration of all 100000 sequences gave 79840 acyclic and 20160 cyclic, in agreement with the formula. This establishes only the marginal count and invariance; it is not a contribution test against an existing rule inventory, and is not a selection policy. No historical inputs, production changes, or claim of mathematical novelty.

Reproduce the local calculation with Python 3.10+ (standard library only):

```python
from itertools import product
from collections import Counter
from math import perm

def canon(ds):
    d = {}
    return tuple(d.setdefault(x, len(d)) for x in ds)

def graph(ds):
    es = {tuple(sorted((a,b))) for a,b in zip(ds,ds[1:]) if a!=b}
    return len(es)-len(set(ds))+1

patterns = sorted({canon(ds) for ds in product(range(5),repeat=5)})
cyc = [p for p in patterns if graph(p)>0]
assert len(patterns)==52
assert len(cyc)==10
assert Counter(len(set(p)) for p in cyc)=={3:7,4:3}
assert sum(perm(10,len(set(p))) for p in cyc)==20160
assert Counter(graph(ds) for ds in product(range(10),repeat=5))=={0:79840,1:20160}
```

The specialized cross-platform run for the original graph audit is 45778095610. The combinatorial certificate is a local verification and has not been separately executed in CI.
