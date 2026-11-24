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
