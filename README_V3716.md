# PL5 V3.7.16 — Bitmap-powered end-to-end research pipelines

This is an opt-in integration on top of the **full cumulative V3.7.15 research package**. The existing NumPy implementations remain default and mathematically unchanged.

New component: `research_backend/pailie5/basic_filter_catalog_v3716.py`. It reuses V3.7.14 exact bitmaps for static `BasicConstraint` rules, supports explicit invalidation, and never caches history-dependent pattern conclusions.

Three established PL5 workflows were integrated in the cumulative ZIP:
- Basic constraints + time-series pattern intersection
- Full 100,000-ticket rank generation and rolling rank backtest
- History-derived sculpting knives and rolling sculpting backtest

**Reproduction:** The full cumulative ZIP contains patched `basic_filters.py`, `probability_ranker.py`, `sculpting.py`, `benchmark_bitmap_workflows_v3716.py`, regression tests, and two 15-repeat benchmark JSON reports.

Measured warm end-to-end speed ratios, legacy / cached:
| Workflow | seed 3716 | seed 3717 |
|---|---:|---:|
| Pattern + basic intersection | 1.543x | 1.344x |
| Rolling rank | 0.923x | 1.051x |
| Rolling sculpt | 1.005x | 1.023x |

Research backend 859/859 and historical integrations 29/29 passed on Linux; a fresh extraction passed all 8 new tests and all 29 integrations.

**Critical limitation:** The GitHub research branch still does not contain the complete 2,556-file cumulative source baseline and cannot currently serve as a standalone reproducible checkout. Use the independently verified full ZIP for reproduction until the P0 cumulative-source migration is resolved. History comes from the bundled *synthetic* demonstration CSV, not authenticated lottery data. No lottery prediction improvement is claimed.
