# PL5 V3.7.44 — frozen-filter intersection conflict certificates

## One falsifiable engineering question

At a fixed K=100 candidate budget per method, can the six existing
candidate-generating filter methods from V3.7.43 safely be combined by
**Boolean intersection**, or does the intersection frequently become
empty? Find the smallest conflicting subfamilies rather than blindly
stacking more filters. This work **adds no new filter rule**.

The finite universe is precisely the 100000 five-digit IDs
`00000` through `99999`. For methods `i` with frozen candidate
sets `S_i` and a subset mask `M`, we compute

`I(M) = intersection(S_i for each selected bit i in M)`.

A nonempty rule portfolio is infeasible exactly when `|I(M)|=0`.
A minimal conflicting portfolio `M` is one with `|I(M)|=0`,
but removing any single selected method yields a nonempty
intersection. By the monotonicity of intersection, these
single-removal checks suffice to prove minimality: all smaller
proper subportfolios must also be nonempty.

## Input and evidence boundary

- The **sole** source is an unmodified **V3.7.43 frozen,
  hash-verified, chained 24-window JSON experiment** from the
  repository's `data/synthetic_demo.csv`.
- Each of the six existing methods outputs **exactly 100 distinct**
  identities for every window. These are full candidate ID sets, not
  approximations by top-score summaries.
- The V3.7.43 source ledger was created by training on strictly
  preceding records, freezing all K=100 candidate sets and their
  SHA256 identifiers **before** evaluation of that window.
- This audit reads candidate membership and panel/source hashes.
  It does **not** consult observed evaluation IDs in constructing
  or measuring intersections. The source verifier separately
  checks the integrity of the supplied sealed record.
- All findings are **INTERNAL_SYNTHETIC** engineering development
  observations. The study cannot establish historical coverage or
  historical exclusion rates on authenticated records.

## Exact scope and independently checkable certificates

For each of the 24 windows, enumerate every one of the
`2**6 - 1 = 63` nonempty subsets, using bitwise AND over the
full 100000-bit membership masks. Persist:

- Source experiment root SHA256 and original input-data SHA256
- Source panel SHA256 for each individual window
- Six fixed method identifiers and their fixed equal K=100 budget
- Subset mask, **exact retained cardinality**, and 100000-bit
  little-endian **SHA256** for each of the 63 intersections
- Every **minimal empty-intersection subset** as its integer mask
- Exact count of empty two-method intersections per window
- Aggregated 24-window conflict-core counts by subset size

An independent verifier rechecks all 63 intersections with **Python
set intersection plus a fresh bytearray** (not the builder's int
bitmask algorithm), and compares the entire JSON data structure.
Tests mutate counts, SHA256 fields, windows, candidate budget,
method order, source root and minimal conflict lists; each mutation
must fail closed.

## Actual fixed-fixture observation — not an effectiveness ranking

Independent direct set enumeration of the previous, unchanged
V3.7.43 archived full-candidate JSON
(root chain `6b9f96e6f1a4f38b60f7ca1f50d927e63049c8da8a22ccf253bdbcd76727ecd3`)
gives the following exact counts:

| Measure | Exact result |
|---|---:|
| Windows | 24 |
| Methods per window | 6 |
| Candidate count per method | 100 |
| Nonempty method subsets evaluated | 24 × 63 = 1512 |
| Two-method pair/window comparisons | 24 × 15 = 360 |
| **Empty two-method intersections** | **255 / 360** |
| **Minimal conflicting pairs** | **255** |
| **Minimal conflicting triples** | **1** |
| Four-, five-, six-way minimal cores | **0** |
| Empty all-six intersections | **24 / 24** |

In synthetic window **000992**, the triple consisting of the
ensemble, positional and seeded uniform methods has empty intersection
despite all **three of its pairs being nonempty**. This is a genuine
minimal *three-method* conflict core, not one caused by a disjoint pair.
Other multi-method empty intersections are typically explained by a
smaller conflicting pair.

The correct negative conclusion is precise: **blind intersection
of these particular equal-K=100 candidate sets frequently produces
an empty candidate set, and adding more of these fixed narrow sets
cannot repair it.** Do not use this subset conflict result to infer
which method is effective, or to infer performance on historical
records. Union, intersection, weighted selection and sequential
compression are distinct engineering operations and must not be
reported interchangeably.

## Reproduction and CI gates

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_filter_conflict_certificates_v3744.py tests/test_filter_fair_longitudinal_v3743.py tests/test_filter_fair_ledger_v3742.py
python -m pailie5.filter_fair_longitudinal_v3743 --output ../../ci-results/v3744-frozen-local.json
python -m pailie5.filter_conflict_certificates_v3744 \
  --frozen-input ../../ci-results/v3744-frozen-local.json \
  --output ../../ci-results/v3744-conflicts-local.json
```

The separate [V3.7.44 GitHub Actions workflow](https://github.com/meilin2026dh/pl5/actions/workflows/pl5-filter-conflicts-v3744.yml)
runs this acceptance matrix on **Ubuntu and Windows, Python 3.12**,
preserving the original 24-window frozen source and all derived
certificates as independent artifacts. Both outputs refuse to
overwrite a pre-existing file. The **complete clean-machine
Python/history regression** and application checks are separate
independent gates; any failing gate blocks total acceptance and
does not authorize merging into `main`.

## Next falsifiable research question (not implemented here)

A future controlled experiment could compare nonempty-preserving
intersection policies with simple exact set baselines under
**identical retained-count and compute budgets**, measuring
sequential marginal exclusions and the cost of early conflict
detection. Such a policy must be evaluated with future-only
frozen windows, not selected after inspecting their outcomes.
