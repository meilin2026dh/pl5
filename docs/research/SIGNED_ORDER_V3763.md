# V3.7.63 — Exact weighted order for signed filtering rules

## Scope and falsifiable question

V3.7.31 already proves an optimal short-circuit order for positive-only conjunctions and a unit checking-cost proxy. V3.7.62 defines twelve frozen rules, with signed complete assignments forming disjoint candidate sets. Extend the existing order theorem to **all signed partial assignments and heterogeneous positive integer cost weights**, then quantify the gap between exact order and simple baselines for every nonempty complete assignment with 1 <= K <= 100. This is one order-optimization task, not a new filter or new threshold.

## Method

Each rule takes a ternary state: omitted (0), required false (1), required true (2). The total state inventory is 3^12 = 531,441. Let n(S) denote the exact number of surviving identities in the signed conjunction S. Fill complete assignment counts from the frozen V3.7.62 masks; for an omitted rule, obtain n(S) by summing its two disjoint signed children. Cross-check every ordinary positive-only state using direct bitmaps and every complete signed state using the frozen atom counts.

For an abstract per-candidate cost c_i > 0 independent of evaluation order, the cost of applying a literal last is c_i n(S minus i). Thus W(empty)=0 and W(S)=min_i[W(S minus i)+c_i n(S minus i)]. Induction establishes optimality because the final set of the prefix is independent of its order. This minimizes modeled scalar checking cost only; it does not estimate runtime, vectorization, cache effects, rule construction cost, or planning overhead.

Compare the deterministic optimal order with (a) fixed rule-index order, (b) unconditional removal-per-cost greedy, and (c) conditional removal-per-cost greedy. Use integer weights, exact rational comparisons, deterministic ties, and two fixed sensitivity scenarios: unit weights and the declared abstract heterogeneous vector (1,1,1,1,1,1,4,4,4,5,3,8). The second is illustrative, not a timing calibration.

Report the number of feasible signed conjunctions (may include duplicates), total modeled cost, exact regret counts and maximum regret across all 893 capped complete atoms. Sum of costs represents a hypothetical workload evaluating each atom once separately, not a shared execution plan or one candidate set. No ordering may change its final candidate membership. Independently replay all four orders with direct bitmap intersections for every capped atom and both scenarios.

## Acceptance

- Small-domain exhaustive permutation oracle for every signed state, including duplicates, empty masks and conflicting restrictions.
- Reject out-of-bounds inventory and invalid weights.
- Full-domain exact count and order replay, stable little-endian hashes of counts, all optimum vectors, and capped-atom cost ledgers.
- Ubuntu and Windows Python 3.12 targeted CI; compare full machine-readable output exactly before cross-platform acceptance.
- Separate application CI remains an additional acceptance gate.

Run:

```sh
python docs/research/experiments/signed_order_v3763.py
```

No historical rows are opened or selected; no new historical coverage or false-deletion result is measured. No rule weights tuned to observations. All new code INTERNAL/AI_AUTHORED. Existing data and hashes unchanged. No main changes, merge or production promotion.

## Upstream status verified 2026-11-24

PR #11 head b5687f5e848d1fab567fcd15d8b1eb51d9e3b651: 5/5 returned workflows passed. PR #13 head 53425be6a80533c219f097e023209776b3330f24: 10/10 passed. Issue #12 remains open. Main base SHA c0e38040ec5f389d6444e64b90e7adc42adfca62. PR #30 evidence head b93cb8dde0222b1386cf37d48761a4b102a79e47: targeted run 45377056496 and application run 45377056557 both passed. Earlier application timeout remains in the failure lineage; no silent removal.

## Verified results — 2026-11-24

Exact tested head: `f0be19133e74e41dddd8e22d7cf93d514fa56f18`. [Targeted CI 45386515806](https://github.com/meilin2026dh/pl5/actions/runs/45386515806) passed Ubuntu and Windows Python 3.12, each with three tests. Full machine-readable JSON outputs were compared character-for-character and are identical. No candidate membership changed for any of the tested execution orders.

All 531,441 signed states were counted; 332,360 are nonempty (including the unconstrained state), and 135,641 signed conjunctions retain 1–100 candidates (not necessarily distinct sets). The cost comparison workload is the 893 nonempty capped complete assignments, not the entire 135,641-state collection.

| Modeled cost, sum over 893 assignments | Unit | Heterogeneous abstract |
|---|---:|---:|
| Exact optimum | 101041383 | 112358214 |
| Fixed order | 182262932 | 192681161 |
| Static greedy | 101668499 | 114056860 |
| Conditional greedy | 101055059 | 112367919 |
| Optimum reduction vs fixed | 44.56285% | 41.68697% |
| Conditional greedy excess vs optimum | 0.013535% | 0.0086376% |
| Conditional greedy strictly suboptimal assignments | 116 | 77 |
| Conditional greedy maximum absolute regret | 2696 | 3330 |

Exact optimum is a reproducible reference, but conditional greedy is nearly optimal in aggregate on **this fixed workload and these two abstract weights**. This is a useful negative result against making expensive exact planning the default. Neither method has measured wall-clock speedup, amortization cost or general performance guarantee; the offline planner and conditional selection overhead are excluded from these sums. Keep both methods experimental; an end-to-end benchmark with calibrated rule costs and planning overhead is required before selecting a default. No historical coverage or error rate is inferred from an order-only experiment.

Reproducibility fingerprints (same on both platforms):

- State-count SHA256: `ab1e118d167b8a80cd47ed0ba341ac678785d81c7f16de708007892f76c0bc62`.
- Unit optimum vector: `9dcc32e6e8b9fcbfd8eba3eaac3f3d2ebacdaeb2a8fa08b34f4799923be85266`.
- Heterogeneous optimum vector: `37698b1fbfc069dab54d0641ea3e0714b75a92193053a6f5863ccd79f83e43fd`.
- Unit capped-atom ledger: `d1272ec7cc3fdffb222bd329c6ea0f9002e91e1b15683ad74fc67dde35d48fb8`.
- Heterogeneous capped-atom ledger: `33ee8b2a262e3881a44227a3259c46ca00bcf12071dc02e5bd9a0ace0d119d1e`.

Separate [application CI 45386515677](https://github.com/meilin2026dh/pl5/actions/runs/45386515677) failed, with 297 of 298 tests passing and the recurrent 10-second timeout in tests/innovation.test.ts. The earlier V3.7.59 and V3.7.61 timeout records remain in the failure lineage; PR #30 evidence head passed both checks in between. This is not a diagnosis of root cause, nor a full acceptance. Do not raise time limits or change application code to conceal it in this experiment. PR #11 (5/5) and PR #13 (10/10) returned successful workflows; Issue #12 open; main base remains c0e38040ec5f389d6444e64b90e7adc42adfca62. No historical inputs or hashes changed. No merge.
