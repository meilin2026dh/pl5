# V3.7.46 — weighted scalar filter execution-order audit

## Frozen hypothesis

The existing V3.7.31 subset dynamic program charges one unit for each scalar membership probe. V3.7.14's deferred executor instead sorts by per-rule cost hints alone. When rule costs differ and exclusions overlap, both policies may be suboptimal. For a fixed conjunction and positive integer cost per probe, compute an exact weighted ordering and compare with both policies and conditional greedy marginal exclusion divided by cost. Do not alter rule membership.

Let H be the already-applied hard mask, S a subset of rule indices, and N(S) the cardinality of H intersected with those rules. The exact minimum obeys D(empty)=0 and D(S)=min over i in S of [D(S minus i)+c_i N(S minus i)]. This holds because the remaining candidate set depends only on S, not its order. Fixed lexicographic ties ensure reproducibility. At most twelve rules, 4096 subsets and 24576 transitions per solve; two solves (weighted and equal-unit). All baseline traces preserve the identical final bitmap. Empty intersections remain empty, with zero subsequent probes.

## Declared verification cases

- INTERNAL/AI_AUTHORED twelve-ID counterexample: masks 3346, 3078, 3417, 1103; costs 2,4,5,6. Exhaustive permutation oracle gives weighted minimum 68 (0,3,2,1), versus 71 for cost-only and conditional greedy. One ID remains. These are abstract cost units.
- Existing V3.7.39 full-domain recurrence masks, no historical input: hypothetical weights 5,2,1 yield a weighted optimum of 125000 units, compared with 521000 for the equal-unit tie-break order. Cost-only and conditional greedy also reach 125000 (retain this negative result: the exact planner adds no benefit over them on this fixture). All orders retain the same 100 IDs; equal-weight total is 111000 probes.
- Thirty deterministic small-domain cases compared with an independent set/permutation oracle, including hard-mask restrictions and empty intersections. Invalid inputs fail closed.

The cost schedule is a sensitivity fixture, **not measured time**. No claim of real-world speedup, historical coverage or historical exclusion rate. Bitmap compilation, cost calibration, full-mask acquisition, plan computation, cache behavior and candidate materialization are excluded. If masks are already compiled, scalar-probe ordering is not a model of native bitmap AND cost. No production executor changes.

## Reproduction

From the repository root:

```sh
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_weighted_filter_order_v3746.py
```

Source parent: `80b0d56ac8b3ae152fe745198a6f4d0c118462b4` (V3.7.45 technical acceptance record). Prior exact-source CI passed on Ubuntu/Windows: #11 45186730980, #13 45220436713, #15 45242431995. Earlier failure genealogy is preserved in CROSS_PLATFORM_ACCEPTANCE_EVIDENCE_20261124.md. Issue #12 remains open. New source requires its own cross-platform CI. No main, historical records, stored data digests or private files changed; draft only.
