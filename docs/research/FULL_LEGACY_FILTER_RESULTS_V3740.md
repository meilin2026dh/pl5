# PL5 V3.7.40 actual unified filter-method test results

**Evidence grade:** INTERNAL / SYNTHETIC DEVELOPMENT DATA ONLY.
**Full-library audit coverage:** all registered source modules.
**Comparable keep-mask experiment coverage:** all adapted filter families;
not every module is an independently executable filter.

## Recorded source, tests and artifact

- GitHub research branch: `research/audit-prequential-portfolio-20261123`.
- Source/test head under which the evidence was generated:
  `91202c3a222c9ea508c4913c6c6346d0dc919963`.
- [Cross-platform GitHub Actions run #45214353464](https://github.com/meilin2026dh/pl5/actions/runs/45214353464):
  **success on Ubuntu Python 3.12 and Windows Python 3.12**;
  **11 dedicated tests passed on each platform**.
- Complete JSON artifact SHA256 printed by both platform jobs:
  `21801e45e23e1bacb9cc93fb887b0c357d4374439e104757260671c915f65853`.
  The two platform results are byte-identical. Artifacts are attached
  to the Actions run, with the workflow's retention period.
- Repo-owned fixture: `data/synthetic_demo.csv`;
  exactly **1,000 synthetic records**, issue `000001` through `001000`,
  source SHA256:
  `f7812094b6a4c7f6a8b10676c1b6ab95e3a234efdede9ff2786319a2fefc6ff6`.

## The complete method library was not discarded

The source census includes **97 source modules** across original
candidate filters, Boolean/GA-CS optimizers, mathematical operator
research, historical/evidence methods and infrastructure, plus
**128 existing Python test files**. All source module names, roles and
source-byte SHA256 values are stored in the JSON report.

However, **97 modules are not 97 comparable candidate filters**.
A rule-generator, mask validator, indexing layer or optimizer may
not directly output a keep-mask. Rather than invent a result for those
components, the report states why each cannot be assessed under this
specific filter-effects contract. The full Python regression remains a
separate gate.

## Actual comparable filter effects

| Family | Independently measured configurations |
|---|---:|
| Traditional/static digit indicators (existing BasicConstraint engine) | **23** |
| Mapped-space static indicators (the original three representation spaces) | **27** |
| Existing DSC structural keep masks | **5** |
| Existing modular-recurrence keep masks | **3** |
| **Static full-domain filter configurations** | **58** |
| Chronological pattern configurations (past-only, synthetic) | **6** |
| Fixed-100 candidate-set ranking configurations (past-only, synthetic) | **6** |
| **Total measured configurations** | **70** |

Static full-domain retained counts ranged as follows:

| Static family | Minimum | Median | Maximum |
|---|---:|---:|---:|
| Existing basic indicators | 80,000 | 84,000 | 99,000 |
| Mapped-space indicators | 81,104 | 88,725 | 100,000 |
| DSC structural filters | 93,600 | 99,900 | 99,900 |
| Modular-recurrence constraints | 10,000 | 10,000 | 10,000 |

The generic static-indicator threshold construction is explicitly
frozen at the full-domain 10th/90th percentile band, not reconstructed
from historical custom thresholds. Therefore this comparison measures
**standardized original-method adapters**, not every old hand-chosen
parameter configuration. Existing historical versions remain intact.

### Bounded history-conditioned synthetic evaluation

Six pattern-filter configurations each ran **eight** last-issue
past-only tests. Synthetic containment and mean retained candidate
counts (rounded only for display):

| Pattern family | Contained / 8 | Mean retained |
|---|---:|---:|
| Digit-5 pattern | 8/8 | 100,000 |
| Traditional sum/span/odd pattern | 8/8 | 93,861.25 |
| Previous-issue context indicators | 7/8 | 80,650.50 |
| Pick23 mapping pattern | 8/8 | 100,000 |
| Pick41 mapping pattern | 8/8 | 99,469.375 |
| Ternary mapping pattern | 8/8 | 100,000 |

The six fixed-K=100 rank/selection methods (random control,
positional, pairwise, ensemble, heuristic ranking, and multi-space
ranking) each retained **0 of 8** synthetic evaluation records.
This very small sample supports **no method ranking or empirical
improvement claim**. Each method kept exactly 100 distinct candidate
IDs in every evaluated period. The complete candidate and past-prefix
SHA256 fingerprints are present in the attached JSON evidence.

### Equal-input structural compression

A label-free, deterministic bounded conjunction over the 58 static
rule masks selected exactly three **previously implemented**
modular-recurrence constraints, with candidate counts:

```
100000 -> 10000 -> 1000 -> 100
```

This reaches the 100-ID *structural* budget, but is **not a newly
discovered superior combination**. It simply rediscovers the already
known V3.7.39 recurrence construction; the work package makes this
negative novelty finding explicit. Greedy is not globally optimal.

## Unresolved tasks, without hiding earlier methods

The available repository research-backend fixture is synthetic; no
independently authenticated historical original source was used.
Consequently, **authentic chronological historical retention and
historical false-exclusion rates are not yet measured**. Existing
NCA-type methods require external indicator values known before
their aligned observation; such inputs were not fabricated.

Remaining source modules have still been catalogued and covered by
their applicable unit/integration regression, but many need their
own bridge from a frozen operator/rule candidate to a Boolean mask.
The proper next work package is to build such bridges, beginning
with the remaining prior tested rule generators and history-window
algorithms, **without changing or deleting earlier methods**.
Run equivalent candidate budgets, immutable history hashes,
full negative cases, execution time and overlap before a
comparative scientific recommendation.

## Reproduction

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_legacy_filter_matrix_v3740.py
python -m pailie5.legacy_filter_matrix_v3740 \
  --output ../../ci-results/v3740-replay.json
```

Complete technical acceptance additionally requires the separate
Ubuntu/Windows fresh-machine full Python tests and historical hash
replay. This report does not claim that gate without inspecting its
GitHub Actions conclusion.
