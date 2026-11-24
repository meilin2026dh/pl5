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

## Exact first-platform result — tested source SHA `3d5e088ee9ff5c5315117280ddf1461720320355`

Ubuntu Python 3.12 targeted CI passed its three deterministic tests, [Actions #45332355368](https://github.com/meilin2026dh/pl5/actions/runs/45332355368). Windows remains an independent acceptance gate until verified.

| Exact static property | Measured |
|---|---:|
| All possible full-assignment signatures | 1,024 |
| Nonempty signed Boolean atoms | **319** |
| Empty atoms | 705 |
| Nonempty atoms each with K<=100 | **200** |
| Union of those 200 atom candidate sets | **5,082** IDs |
| Smallest nonempty atom | K=1 |
| Largest nonempty atom | K=9,198 |
| Previously frozen smallest-atom arm | signature 1, K=1 |
| Frozen arm historical coverage | 0/20 |
| Historical records in any K<=100 atom | **0/20** |
| Smallest historic target's atomic floor | **K=160** (issue 26278) |
| Largest historic target's atomic floor | **K=9,198** (issues 26281 and 26289) |

The earlier positive-only conjunction grammar had the smallest historical target floor K=406. The signed-literal grammar **strictly expands the construction space** and improves the structural minimum to **K=160** within this same retrospective panel, but still cannot retain any of these 20 historical records with K<=100 using **one signed conjunction over the ten frozen predicates**.

The union of 200 eligible atoms retains 5,082 IDs and is **not** an eligible K<=100 filter. A Boolean OR of atoms could produce different sets, but any OR that retains a record must include that record's entire atom; hence its candidate size cannot be smaller than its atom's K. This extends the infeasibility certificate to *arbitrary Boolean formulas constructed exclusively from these ten frozen binary feature outputs* for the fixed panel, not to any additional mathematical descriptor or future record. This is a stronger static structural theorem, not evidence of improved historical filtering efficacy.

All outcomes remain retrospective and possibly exposed in previous development; no selection based on this history is permitted.

## Cross-platform verification and acceptance limit

[Targeted GitHub Actions #45332355368](https://github.com/meilin2026dh/pl5/actions/runs/45332355368) **passed on both Windows and Ubuntu Python 3.12**, 3 tests per platform, with byte-identical complete `V3759_SIGNED_JSON` results and identical union/candidate SHA256 digests. The tested code SHA is `3d5e088ee9ff5c5315117280ddf1461720320355`; subsequent documentation commits do not alter that source.

**Separate application CI #45332355318 failed:** `tests/innovation.test.ts` exceeded the known 10-second per-test limit (297 tests passed, one timed out). This is a previously observed intermittent failure, and cannot be silently treated as a successful complete-project acceptance. No production changes or app-test modifications were made in this bounded math experiment.

**Decision:** The ten-feature Boolean-grammar representational boundary is precisely characterized for the fixed retrospective panel; do not extend the same rule algebra or select tiny atoms based on these targets. The next truly new scheme must add genuinely different observable information or a separately specified time-forward adaptive construction, with predeclared controls and historical coverage gates. These conclusions are about engineering expressiveness, not about future outcomes.
