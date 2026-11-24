# V3.7.47 — cold/warm execution and planning overhead

## Frozen engineering question
Does the V3.7.46 scalar-probe ordering certificate justify its runtime overhead when complete fixed membership bitmaps are already available? Compare end-to-end elapsed time, not hypothetical cost units. Use the existing V3.7.39 three-rule recurrence fixture and one explicitly INTERNAL/AI_AUTHORED twelve-rule scaling stress fixture (nine redundant supersets of those same rules). No historical input, no change to any existing membership or production executor.

## Measurement protocol
For each fixture, compare input-order scalar byte membership, conditional greedy and exact-audit scalar order, and cardinality-sort, greedy and exact-audit native bitmap AND. Warm/cold paths distinguish reuse from actual mask compilation; cached exact order is also measured with warm masks. For both fixtures an independent constructive enumeration proves the exact same 100 retained identities. Record all five timed repetitions per path, one excluded warmup, deterministic rotation of path order, acquisition/plan/execution-and-materialization elapsed nanoseconds, total elapsed time, scalar probe count, mask hashes, logical cache payload and host software versions. Packing the scalar byte masks is included in execution. Exact audit currently includes two dynamic-programming solves, hashing and reporting; its overhead is that of the current API, not a lower bound for a specialized planner. Cached-plan setup is excluded from cached timing and must be accounted for separately when interpreting reuse.

Native bitmap timing measures a small research path using the existing V3.7.14 bitmap unpacking function, not the full production engine. Scalar timing is a uniform-cost byte membership probe, not a calibrated deferred-predicate cost. The twelve-rule fixture is deliberately redundant, not a representative production distribution. Logical cache payload is not process peak memory. Timings are non-deterministic across hosts; only exact identities, probe counts and structural checks are acceptance criteria. No speed threshold, historical coverage, historical exclusion-rate or general performance superiority claim. Preserve all raw samples including negative comparisons.

## Reproduction
```sh
cd pl5-cumulative/research_backend
python -m pytest -q -s tests/test_filter_runtime_v3747.py
python -m pytest -q tests/test_weighted_filter_order_v3746.py
```
The existing V3.7.46 workflow runs both commands on Windows and Ubuntu Python 3.12. Each test emits a V3747_RUNTIME_JSON line; the complete regression is a separate gate. Prior V3.7.46 frozen source 1da80c81eeca5cd1fd2cd1a703a3967617eaa55e had successful targeted run 45262188233 and full regression 45262188307; earlier CI failure genealogy remains in CROSS_PLATFORM_ACCEPTANCE_EVIDENCE_20261124.md. No change to main, historical records or hashes; draft only. New timing evidence must be inspected after actual CI completion.
