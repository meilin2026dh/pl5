# V3.7.38 — Frozen structural filter inventory: exact portfolio and redundancy audit

## Single preregistered engineering question

Can the five fixed V3.7.37 structural filter rules, applied after the
already-frozen conventional baseline, reduce the full 100000-ID space
to no more than 100 retained IDs? If not, what is the **exact minimum**
retained count and smallest rule subset preserving the full conjunction?

This package adds no features, no fitted cutoffs and no new rule families.
It integrates existing Boolean, Shapley and rule-equivalence engines on
the **unchanged** V3.7.37 masks.

## Fixed inputs and objective

- Domain: `00000` through `99999`, one identity per bit (100000 total).
- Non-optional baseline: `10 <= sum <= 35` and `span >= 3`.
- Optional rule order: modular arithmetic, exact 2-position periodic,
  at-most-2 modular difference values, near-2-position periodic, and a
  duplicate modular arithmetic negative control.
- All `2^5=32` subsets are enumerated. The target is **1..100** retained
  identities; no post-processing to force the target is allowed.
- The exact method is a conjunction of fixed KEEP masks. A full
  conjunction is a subset of every partial conjunction. Therefore
  the full-conjunction survivor count is a **global lower bound**
  for every subset. If that lower bound exceeds 100, reaching the target
  with this inventory is mathematically impossible.

## Independently checked combinatorial counts

The exhaustive 100000-ID enumeration gives this fixed hypothesis
family the following counts:

| Measure | Exact count |
| --- | ---: |
| Baseline retained | 94890 |
| Additional exclusions, progression rule | 90 |
| Additional exclusions, exact period2 (after progression) | 40 |
| Additional exclusions, <=2 modular differences (after prior rules) | 5728 |
| Additional exclusions, near period2 (after prior rules) | 1628 |
| Additional exclusions, duplicate progression control | 0 |
| Net exclusions beyond baseline | 7486 |
| Smallest retained set across all 32 subsets | 87404 |
| Maximum requested retained | 100 |
| Feasible subsets in this inventory | 0 |

**Negative engineering finding:** the five frozen structural rules do
not come close to 100 retained IDs in this baseline. The full inventory
retains 87404; 87404/100000 is the corresponding combinatorial
retention reference.

The existing exact-equivalence engine proves the same full candidate
mask is obtained from just **two** rules:
`exclude_low_delta_diversity` and `exclude_near_period2`
(genome `0b01100`, 1-indexed positions 3 and 4). Three rules can
therefore be removed *without changing any retained identity*.
Their Shapley exclusion attribution can nevertheless be nonzero,
because Shapley averages marginal contributions over all execution
orders. Zero contribution in the fixed sequential order does not imply
zero Shapley credit.

## Code, repeatability and limits

- Source: `pl5-cumulative/research_backend/pailie5/digit_structure_portfolio_v3738.py`
- Tests: `pl5-cumulative/research_backend/tests/test_digit_structure_portfolio_v3738.py`
- Method: exact constraint subsets (V3.7.31), interaction and Shapley
  (V3.7.34), exact equivalent-rule pruning (V3.7.35), frozen DSC rules (V3.7.37)
- Run:
  ```bash
  cd pl5-cumulative/research_backend
  python -m pytest -q tests/test_digit_structure_v3737.py tests/test_digit_structure_portfolio_v3738.py tests/test_constraint_portfolio_v3731.py tests/test_filter_interactions_v3734.py tests/test_filter_equivalent_pruning_v3735.py
  ```
- Tests assert exact counts against a second independent 32-subset loop,
  exact equivalence and Shapley conservation, deterministic hashes,
  the infeasibility certificate and a legitimate empty feasible set.
- No historical data are read and no time-forward historical coverage
  is measured. Negative results are retained rather than changing
  thresholds to manufacture a 100-ID result.
- Scalar predicate-check cost is a structural accounting metric and
  should not be reported as benchmark wall-clock runtime.

## Next possible study gate

Only after the present package has passed Linux/Windows and the
existing full regression should a separate, fixed-budget comparison
test whether a strictly larger, independently specified **rule grammar**
has better compression/complexity tradeoffs. A new rule family must
state a falsifiable hypothesis before implementation. Historical
time-forward analysis, if permitted, must freeze rule definitions and
separate the calibration and evaluation windows.
