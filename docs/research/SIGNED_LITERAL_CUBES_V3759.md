# V3.7.59 — New signed-literal filtering grammar, exact full-domain certificate

## Highest-value frozen hypothesis

The prior ten **positive-only** filters and all their AND subsets cannot cover any of the twenty crosschecked historical records with K<=100. This does **not** prove that the existing ten Boolean features cannot express smaller, differently located candidate sets.

Test **one new filtering construction**, not an extra feature: each existing binary predicate may be required TRUE, required FALSE (complement), or omitted. The signed conjunction grammar therefore includes ordinary AND-only rules and is strictly more expressive when complemented rules split their retained sets. No new numeric thresholds, fitted parameters or target-dependent rule construction are permitted.

## Exact mathematical certificate

For each candidate x in 00000..99999, define a frozen 10-bit truth signature s(x) from the **same V3.7.56 ten rule masks**. The full-assignment Boolean atom A_s is the conjunction of all ten signed literals consistent with signature s. The atoms partition the full domain: A_s are pairwise disjoint and their union is the original 100,000-element universe. Every signed partial conjunction containing x necessarily contains its full atom A_s(x); therefore **|A_s(x)| is the minimum possible retained K** for any signed-literal conjunction containing that particular ID. This is a representational feasibility theorem, not an executable historical selection policy.

The implementation independently constructs every atom through ten direct bitmap intersections of positive or complemented masks, and compares every atom's cardinality with a separately constructed 100,000-element signature histogram. It checks the complete partition union and disjointness and emits a deterministic hash of the union of all nonempty atoms with K<=100.

An explicitly predeclared **domain-only test arm** is selected without outcomes: the smallest nonempty atom, breaking ties by ascending truth signature. This provides a concrete fully explainable candidate-filter example; its retrospective outcome will not be optimized or used to promote the rule. Other atoms under the cap are **diagnostic possible constructions**, not 1000 independently evaluated models.

## Historical retrospective check

Use unchanged, byte-hash-verified transcriptions from V3.7.56 (31 earlier rows and twenty crosschecked terminal rows). Construct all Boolean masks, eligible-atom support, arm signature, membership bitmap and hashes **before** reading historical targets. After freezing, for every target record report its own signed minimum-K floor and previous positive-only floor, along with the indicator that the predeclared smallest-atom arm contained it.

Do **not** select an atom that retrospectively covers those twenty records. Even if some historical targets fall into small atoms, that only disproves the old positive-AND representation constraint; it does not verify historical or future usefulness, and the entire diagnostic capped-atom union may greatly exceed K=100. Every post-hoc per-target floor is **not** a deployable next-window filter. No fresh external authentication or independent unseen test is available.

## Reproduce

```sh
python docs/research/experiments/signed_literal_cubes_v3759.py
```

Three deterministic unittests: toy-domain full signed-atom oracle, full 100,000-element exact counts and retrospective floor conservation, and bitwise replay. Ubuntu and Windows Python 3.12 CI must both pass on the precise source SHA for focused acceptance. Complete regression and application checks are separate gates.

## Research boundaries

All rule definitions are already frozen mathematical predicates; all new combinational masks are INTERNAL/AI_AUTHORED. No refitting, target window selection, source file editing, stored historical-hash modification, production promotion, private files or paid APIs. No main changes, automatic merge or forced push.

This exercise tests **expressiveness and feasibility** only. A large new filtered grammar can trivially produce small arbitrary sets. Real engineering utility requires future timestamped frozen candidate sets, matched-K random controls, historical coverage/error evidence from an unseen independent panel, and execution-cost comparisons. Preserve negative results.
