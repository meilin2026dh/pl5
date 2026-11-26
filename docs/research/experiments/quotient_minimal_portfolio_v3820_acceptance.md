# V3.8.20 cross-platform acceptance — 2026-11-27

INTERNAL/AI_AUTHORED. Exact minimum-cost static union-implication certificate for elementary quotient graph filtering rules.

- Tested head: 8bbf3da159d657c915fa08e0d6914488acc8c2bd
- Algorithm source commit: ce838f85056188f9b2551c68716d2186888cbc0e
- Source blob: 41c6be8d8ce99e524bf47ba2117f9dad0562a616
- Reproduce: `node docs/research/experiments/quotient_minimal_portfolio_v3820.js`
- Specialized run: https://github.com/meilin2026dh/pl5/actions/runs/45879834313 — success.
- Ubuntu job: https://github.com/meilin2026dh/pl5/actions/runs/45879834313/job/140116077441 — success, explicit certificate step 41 succeeded.
- Windows job: https://github.com/meilin2026dh/pl5/actions/runs/45879834313/job/140116077781 — success, explicit certificate step 41 succeeded.
- Application run: https://github.com/meilin2026dh/pl5/actions/runs/45879834314 — success.

Both job logs contain identical structured output (all six frozen rows verified by workflow):

```json
{"audit":[{"cost_profiles":6,"minimal":1,"n":1,"portfolios":1,"valid":1},{"cost_profiles":6,"minimal":1,"n":2,"portfolios":2,"valid":2},{"cost_profiles":6,"minimal":0,"n":3,"portfolios":8,"valid":0},{"cost_profiles":6,"minimal":16,"n":4,"portfolios":64,"valid":38},{"cost_profiles":6,"minimal":110,"n":5,"portfolios":1024,"valid":958},{"cost_profiles":6,"minimal":435,"n":6,"portfolios":32768,"valid":32627}],"source":"INTERNAL/AI_AUTHORED"}
```

12,201 abstract words, 33,867 portfolios and 36 cost-profile/space cases including zero costs, ties, infeasibility and forced triangle. Exact minimum costs agreed with exhaustive comparison. All inclusion-minimal covers for n>=4 are nontriangle triples; cheapest three edges suffice unless they form a triangle, in which case replace the third with the fourth. Nonnegative additive costs only. This is static union implication, not full union equivalence; no general portfolio optimality, measured runtime improvement, candidate-set compression improvement or historical coverage benefit established.

## Evidence lineage

Source-head runs 45878175168 and 45878175158 succeeded but lacked explicit V3.8.20 invocation; superseded for this certificate by step-41 evidence above. V3.8.19 archive-head runs 45877966568 and 45877966701 succeeded. Historical Windows timeout cancellations preserved in previous PR records. Main at c0e38040ec5f389d6444e64b90e7adc42adfca62; PR #11/#13 remain drafts with 5/5 and 10/10 successful associated runs; Issue #12 open. No production or historical data changes, no merge. This evidence-only archive does not certify its own subsequent CI.
