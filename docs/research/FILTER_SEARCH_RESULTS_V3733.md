# V3.7.33 actual cross-platform synthetic filter-portfolio results

**Status:** INTERNAL deterministic filtering benchmark, **not** lottery forecasting.

## Frozen protocol and code

- Source commit under evaluation: `ae55ba4932721eeb49d7339c5691dc63fc75224b`
  (benchmark source `131e7640d83322e57f18d10246aeb8caef742ef9`,
  tests `c166cf4fce93063783e964a0d7c234997df6059c`).
- Four predefined mask families, five fixed seeds, eight optional masks each,
  exhaustive 256-genome oracle, 32 counted genome evaluations per bounded
  method per trial, GA-CS versus random. **20 paired trials.**
- Cross-platform workflow:
  https://github.com/meilin2026dh/pl5/actions/runs/45201432079
- Exact targeted test command in the workflow:
  `python -m pytest -q tests/test_filter_search_suite_v3733.py tests/test_filter_search_oracle_v3732.py tests/test_constraint_portfolio_v3731.py tests/test_ga_cs_optimizer_v3715.py`.
- Experiment command:
  `python -m pailie5.filter_search_suite_v3733 --output ../../ci-results/v3733-filter-synthetic-<OS>.json`.

## Actual observed result (from recorded GitHub job logs)

| Paired result | Count |
|---|---:|
| GA-CS alone reached exact scalar-objective optimum | **1** |
| Random alone reached exact scalar-objective optimum | **1** |
| Both reached exact optimum | **1** |
| Neither reached exact optimum | **17** |
| Total trials | **20** |

- Ubuntu Python 3.12 job `137785662279`: **34 tests passed**.
- Windows Python 3.12 job `137785661802`: **34 tests passed**.
- Both jobs printed identical JSON SHA256 for complete synthetic result:
  `a4e1db4e432766914d2bd5c48a8479a9f451dc78afb45ce95354430082d4bd52`.
- The workflow uploads the complete JSON output for traceability; the
  above counts and digest were read from recorded GitHub Actions job logs,
  **not invented**.

## Conclusion and negative-result interpretation

For this narrow, deterministic 20-trial suite, **GA-CS did not show an
observed advantage over random portfolio search** in reaching the exact
scalar objective at the fixed evaluation budget: each won alone once, both
succeeded once, and both missed in 17 trials. This does not prove the
methods are identical or that GA-CS never helps; it is a deliberately
limited, developer-authored engineering fixture, not an independent
generalization experiment.

Equal *objective evaluations* are not equal elapsed time. This analysis
cannot establish robustness on real filtering inventories, a better
Pareto frontier, or historical draw containment. The latter must be
investigated separately using frozen rules and chronological historical
data, without optimizing on test-period outcomes.

The existing PR remains draft. General clean-machine Python acceptance
is a separate gate and must not be inferred from these focused results.
No draw history, unknown test answers or private keys were accessed in
the experiment. No future predictive advantage is claimed.
