# V3.7.41 — cafast covering-array bridge and independent full-tuple verification

## Engineering purpose

For five decimal factors and strength t, identify a small family of five-digit
identities that contains every value tuple for every t-column subset.
The number of required interactions is exactly C(5,t)*10^t:

| t | Required tuple obligations | Elementary row lower bound |
|---|---:|---:|
| 2 | 1,000 | 100 |
| 3 | 10,000 | 1,000 |
| 4 | 50,000 | 10,000 |

This is **digit-interaction coverage**, not 100,000 complete-string
coverage. An array can satisfy all t-way obligations while containing
only a small fraction of the complete five-digit space.

## Why reuse V3.7.13 rather than replacing it?

The repository already implements an algebraic GF(11) polynomial covering
construction at t=2/3, followed by the surjection 10->9 (decimal levels).
It produces **120 rows at t=2** and **1330 rows at t=3**, with the
existing `covering_arrays_v3713.audit_interactions` verifier. Those
numbers already beat the user-supplied 125 / 1338 examples.

This work package extends the identical original algebraic construction
to **t=4**, where it produces 14,361 rows with complete four-way coverage.
It then applies a reproducible, conservative seeded row-removal optimizer.
A row is removed ONLY when every one of its t-way interactions currently
appears at least twice. This invariant preserves coverage at every
intermediate step. Exhaustive independent counters and the old V3.7.13
verification check the final set.

With seeds `0..31`, an initial local CPython implementation
observed the following *feasible upper bounds* (not optimality proofs):

| t | Starting rows | Best retained after 32 deletion orders |
|---|---:|---:|
| 2 | 120 | **119** |
| 3 | 1330 | **1288** |
| 4 | 14361 | **12367** |

The t=4 result is 13 rows above the supplied example of 12,354; it is
not an improvement over that example. Comparisons are meaningful only
if both row sets pass the same tuple coverage certificate.

The elementary lower bounds 100 / 1000 / 10000 do **not** prove that
those lower bounds are attainable for all five columns. The best
observed row count is also not a proven mathematical minimum.

## CRAN `cafast` integration

The current CRAN package is `cafast` **0.1.1** (2026-11-14),
a GPL-3-or-later R package with compiled C routines, R >=4.0 and
`CAs` dependency. It is not identical to a generic random-batch
greedy covering-array constructor. Relevant exported functions:

- `count_core(x, t, vs=rep(10L,5L), rowmult=TRUE)` — exact
  tuple multiplicities, thin and missing tuple diagnostics
- `postopNCK_c` — randomized NCK covering-array post-optimization
- `powerCT_any` — structured power construction

`caverify::ca_verify` is an independent compiled verifier.
The CI workflow builds CSVs with five integer columns (0..9), installs
the actual CRAN `cafast` and `caverify` in an Ubuntu R environment,
calls both `cafast::count_core` and `caverify::ca_verify` on t=2/3/4,
and fails if a single tuple is absent. The counts and version numbers
are archived with the Python witness files.

**Local environment limitation:** No local `Rscript` interpreter was
available when this branch was authored. The Python code was executed
locally, but the external compiled R package must be confirmed from the
actual GitHub Actions logs. Do not claim the R dependency ran unless
the `actual-cran-cafast` job succeeds.

No upstream GPL C source is copied or redistributed into PL5. The
integration is a separate, version-checking subprocess and
interchangeable five-column CSV format.

## Repeatable experiments

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_covering_arrays_v3713.py tests/test_cafast_covering_bridge_v3741.py
python -m pailie5.cafast_covering_bridge_v3741 --outdir ../../ci-results/covering-v3741
cd ../..
Rscript ci/cafast_verify_v3741.R ci-results/covering-v3741
```

The generator refuses to overwrite an existing experiment directory;
the 32 seed outcomes, best set SHA256 and missing/thin tuple counts
are preserved in `summary.json`. Full CSV rows are attached to GitHub
Actions, not pasted into chat.

## Precise limits and future work

1. Partial-digit coverage is guaranteed when missing tuple count is zero,
   but this does not certify any particular full five-digit identity's
   presence.
2. The row-removal phase cannot add new identities or alter symbols,
   whereas NCK post-optimization may restructure rows; compare under a
   common independent verifier.
3. A *thin tuple* seen exactly once marks fragility of t-way coverage:
   deleting its unique holder would break a requirement. This is a
   mathematical necessity witness, not a reason to alter the array
   based on an external observed outcome.
4. t=4 is still above the provided 12,354-row example; new search and
   randomized NCK optimization should be assessed only after the
   compiled CRAN baseline is reproducible.
5. These covering arrays and the existing constraint-portfolio
   compression modules solve different engineering objectives.
   Keep separate metrics, provenance, and acceptance gates.
