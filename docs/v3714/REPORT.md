# PL5 V3.7.14 — Actual performance acceptance

## Scope
- Universe: all 100,000 PL5 tickets, indexed 00000–99999.
- Original comparison: the actual vectorized NumPy `pailie5.basic_filters.apply_basic_filters`, NOT an intentionally slow Python loop.
- 20 deterministic static constraints: digit locations, sums, parity, span, diversity, repetition.
- Seed 3714, 20 rounds, 20 query configurations per round (4/8/12/20 conjunction rules).
- Every returned integer ticket compared with NumPy via exact ordered array equality.

## Measured on the available Linux runtime

| Measurement | Result |
|---|---:|
| Comparisons | 400 |
| Result differences | 0 |
| Original NumPy median | 1.855 ms |
| Exact bitmap warm-query median | 0.213 ms |
| Warm-query median ratio | 8.70× |
| Original NumPy P95 | 3.861 ms |
| Bitmap P95 | 0.459 ms |
| Cold build + 20-rule conjunction | 3.948 ms |
| Replace one rule + recompute all | 0.622 ms |
| 20 rule bitsets | 250,000 logical bytes |
| Python integer bytes for 20 | 265,432 |
| 20-rule combined survivor count | 28,672 / 100,000 |

## Functional verification
- 8 targeted new tests pass, including mask bounds, digit padding, exact AND/OR/NOT, cache invalidation, replace/delete, mutation resistance and delayed predicates.
- First backend full run: 836 passed, 1 V3.1 historical CLI timeout at 30s; isolated rerun succeeded in 4.65s.
- Second backend full run: **837 passed** in 188.76s.
- Historical integration suite: **29 passed**.
- Cumulative ZIP: **2,518 source/test/doc files**, plus manifest, legacy V3.7.12 2,489 files byte unchanged and V3.7.13 15 files overlaid.
- Fresh extraction: 2,518 SHA256 matches, 8 targeted tests and 29 integration tests pass.

## Boundaries
- Bitmap cache is a performance layer; it is not a lottery forecasting algorithm.
- Dynamic external state requires explicit invalidation of dependencies; no automatic stale-context detection.
- No Bloom filter: exact 12.5 KB-per-rule dense bitsets are appropriate for this small fixed domain.
- Warm benefit depends on reusing cached rule masks; single cold queries may not be faster.
- Windows Python 3.12 runtime and a full React build have not been verified.
