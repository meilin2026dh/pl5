# PL5 V3.7.40 — historical method census and unified filtering-effect matrix

## Why this work package was necessary

Earlier DSC comparisons used only a conventional sum/span baseline. That
was insufficient to represent the many existing PL5 versions and
research methods. This work package audits **every current Python
source module** in `pailie5/`, then runs all directly compatible
registered static indicators and explicit history-conditioned filter
adapters through one transparent evaluation contract.

The original method implementations are reused, not reimplemented as
unrelated rules. The source-census step reports exact source-file SHA256
and fails if any new source file lacks an explicit research role.

At implementation time, the connected GitHub branch contained **97 Python
source modules** and **128 test files**. These inventory counts must be
rechecked in the CI output because every code addition changes the
snapshot.

## Separate unlike computational methods

The census assigns every module exactly one role:

1. Direct candidate-filter families (basic constraints, time-series
   filters, multi-space transforms, DSC, modular recurrences and
   candidate ranking).
2. Boolean combination search and optimization (GA-CS, exact subset
   enumeration, Pareto, compression, equivalent-rule pruning).
3. Mathematical operator and grammar research (autonomous operator
   invention, latent and adaptive structures, transfer methods).
4. Historical/evidence evaluation (chronological tests, dataset
   reconciliation, audit and provenance).
5. Infrastructure (data loading, registries, APIs, transport).

**These are not interchangeable units.** An optimizer needs a fixed
mask inventory to operate on; an algebraic research experiment is not
necessarily a Boolean filter; an external-association model requires
a genuine prior-available external input. Their source entries are
included but cannot be assigned fabricated candidate-count or retention
statistics. The entire existing Python test suite is a separate
technical regression gate.

## Exact executable candidate-set comparisons

`pailie5/legacy_filter_matrix_v3740.py` reuses:

- Every fixed standard indicator from `indicator_table()`, compiled
  with **the existing** `BasicConstraint` and
  `apply_basic_filters` implementations.
- Every registered **static** metric from the three old representation
  spaces: `pick23_6`, `pick41_4`, `ternary11`. It intentionally
  excludes arbitrary test-registered or external indicators to keep
  results stable across Python test collection order.
- All five DSC fixed rule definitions, including the explicit
  duplicate control.
- All three exact modular recurrence conditions.
- Six fixed time-sensitive pattern configurations, over the last
  eight issues of a repository-owned *synthetic development demo*,
  calling original `pattern_rules.filter_next` with only earlier rows.
- Six matched 100-candidate subsets per issue from original positional,
  pairwise, ensemble, random control, heuristic ranking and multi-space
  ranking interfaces. Every candidate set is frozen before that issue's
  demo record is evaluated.

Each static mask reports **its own** candidate count, exclusions,
full-bitmap SHA256 and demo-record containment. For every dynamic
method/issue, the report stores input-prefix SHA256, candidate SHA256,
count and observed synthetic containment. Methods with different
candidate counts are not conflated: the rank cohort has a fixed
K=100; the pattern cohort reports its actual variable counts.

The static thresholds are derived from frozen **full-domain** 10th and
90th percentile values, not from the demo outcomes. This is a declared
shared method of constructing constraints; it does not recreate every
historical manual threshold. Every selected rule's parameters appear
in the output, so its exact semantics are auditable.

A bounded label-free greedy conjunction search uses the **same union
of old and new static masks**, with at most 12 rule additions. It
reports count, exact candidate fingerprint and each step. This
is not a proof of global optimality, and an empty set is refused.

## Provenance limitation — do not invent historical results

The directly inspectable data file in the research backend is
`data/synthetic_demo.csv`. This is **not** a cryptographically
authenticated original historical ledger. The source audit deliberately
does not read hidden, unreleased or private answers, and does not
substitute a made-up historical dataset. Therefore:

- The demo containment figures are `INTERNAL_SYNTHETIC_DEVELOPMENT_ONLY`.
- Authentic historical coverage and false-exclusion performance are
  **NOT MEASURED** in this package.
- External-alignment research such as NCA remains blocked for
  authentic context until data provenance is established.
- Modules without a same-contract keep-mask adapter remain listed as
  `SEPARATE_COMPONENT_CONTRACT_NOT_A_SINGLE_STATIC_KEEP_MASK`,
  rather than silently omitted.
- A single historical sample score never becomes a basis for
  modifying thresholds in this fixed comparison.
- All previously stored source and historical SHA256 values remain
  unchanged. No `main` merge is authorized.

## Reproducible commands and evidence

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_legacy_filter_matrix_v3740.py
python -m pailie5.legacy_filter_matrix_v3740 \
  --output ../../ci-results/v3740-local.json
```

Dedicated Windows/Linux Python 3.12 CI:
`.github/workflows/pl5-legacy-allmethods-v3740.yml`.
The workflow emits full JSON artifacts for the same fixed demo,
source code SHA256 census, every measured filter, each test-period
candidate SHA256 and all unmapped-component explanations.

The existing **full clean-machine Python suite and history replay**
also runs independently on the draft PR. Only completion of all
required cross-platform gates permits technical acceptance.

## Next research work package

Once the all-module census and synthetic matrix pass, obtain or verify
a specifically permitted **public authenticated historical ledger**
without changing original data digests. Freeze a train/validation/test
chronological protocol and all rule inventories before scoring.
Then run fixed-size comparable historical containment and false
exclusion tables for the subset-producing methods, while keeping
optimizer/original-operator effects separate.

Do not describe this present synthetic audit as a completed
authentic-history comparison.
