# V3.7.33: fixed-filter portfolio search — paired internal benchmark

This is **filter-combination engineering only**. It does not predict numbers,
use historical draw labels, or assert that a compressed candidate set is
more likely to contain a future independent uniform draw.

## Fixed pre-evaluation design

The same pre-existing V3.7.15 objective is optimized by the **random**
search and by **GA-CS**, each using 32 counted candidate evaluations per
seed, including repeated proposals. The exact oracle evaluates all 256
portfolios in each eight-rule inventory, separately from the restricted
optimizer budgets. The fixed seeds are 373301..373305, making 20 paired
family/seed trials and 40 constrained optimizer runs.

Four deterministic, developer-authored rule inventories on 4096 candidate IDs:

- **nested** — progressively tighter nested kept masks, including a
  known feasible 100-candidate mask
- **orthogonal** — digit-bit positional tests making intersections shrink
  predictably, with nonidentical overlaps
- **redundant** — repeated and duplicate keep masks, including the full set
- **conflicting** — incompatible half-universe rules and a few unrelated
  constraints, to force some empty intersections

These are synthetic stress tests, not a representative distribution of
real-world filtering rules. No family is selected based on observed results.
All trial results, including those where both methods fail or random wins,
must be retained. Each run includes the full source-mask inventory SHA256,
all seeds, per-arm evaluation counts and objective gap to the exact oracle.

The reported paired table has four exhaustive categories: GA-CS alone reaches
the oracle, random alone reaches it, both reach it, or neither reaches it.
A single positive comparison is **not** evidence of algorithmic superiority;
this study reports descriptive counts only and does not perform statistical
significance testing. Equal objective evaluations are not equal runtime.

## Reproducible commands

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_filter_search_suite_v3733.py tests/test_filter_search_oracle_v3732.py tests/test_constraint_portfolio_v3731.py tests/test_ga_cs_optimizer_v3715.py
python -m pailie5.filter_search_suite_v3733 --output ../../ci-results/v3733-local.json
```

`.github/workflows/pl5-filter-search-suite-v3733.yml` executes the same
fixed run on Ubuntu and Windows Python 3.12; it uploads complete JSON
artifacts for cross-platform comparison. The benchmark refuses to overwrite
an existing evidence file. Only after the Actions have completed can the
recorded fixture-specific success/failure counts be discussed.

## Limitations and follow-up gate

- These are **INTERNAL / DEVELOPER_AUTHORED** fixtures and remain a development
  suite forever, not independent third-party blind tests.
- The exact oracle and search use V3.7.15 *scalar fitness*, not V3.7.31's
  three-objective Pareto metric. Never conflate their optimality criteria.
- The static inventory, not draw outcomes, determines the best engineering
  genome. Real historical containment, false exclusions, structural
  stability, rule-generation quality and CPU time are unmeasured.
- Frozen-mask hashes establish reproducibility, not source authenticity or
  external certification.
- An effective next research package is to report independently frozen,
  time-forward historical containment **separately** from this benchmark;
  no target-time outcome may enter rule choice, and no claim of lottery
  prediction advantage is permitted.
