# V3.7.57 — Are 308 apparent failures 308 independent observations?

## Frozen high-value audit question
V3.7.56 showed that, among all 1,024 intersections of the same ten predeclared mathematical filters, **308** subsets satisfy `1 <= K <= 100`, but **none retains any of 20 crosschecked retrospective target records**. Before adding any new rules, test the falsifiable hypothesis that these apparently numerous failures arise from highly overlapping candidate sets, with a very small **union support**. The support is the exact Boolean OR of all 308 admissible AND sets. It is **not** a new production filtering rule or a selectable candidate arm.

## Exact audit and independent oracle
- Recompute all ten frozen rule masks, all 1,024 Boolean intersections, and identify exactly the 308 nonempty capped sets without reading outcomes.
- Compute the **union bitmap** using native integer OR; independently regenerate by bytewise OR over all 308 individual 12,500-byte masks; compare every ID and hash the full union.
- Compute exact numbers of *unique* admissible masks, distribution of K and union cardinality `U`.
- Only **after** all candidate memberships are frozen, read the same 20 original, dual-transcription crosschecked retrospective target records. Count whether each target is in the union and how many admissible subsets include it.
- Use a clearly labeled **hypothetical independent uniform-ID reference**, not an inference about outcomes: expected union coverage `20U/100000` and probability of zero `(1-U/100000)^20`. This merely quantifies whether zero can be commonplace given the very small union.
- Do not treat 308 overlapping sets as 308 independent trials. Do not select a rule based on this same retrospective panel, claim historical superiority, or discard empty intersections.

## Reproduce
```sh
python docs/research/experiments/k100_union_audit_v3757.py
```
Three tests assert frozen 308 eligible and 68 empty masks, exact bytewise OR oracle, per-window containment conservation and deterministic replay. Cross-platform checks on Windows and Ubuntu Python 3.12 must pass **for the exact source SHA** before technical acceptance.

## Evidence limits
Historical data provenance remains the same as V3.7.56: 51 primary transcribed records, only 20 terminal records crosschecked with a second table. Original source pages and external historical timestamps are not independently authenticated. Static filters may have been explored against earlier data in prior research; this is not a truly unseen independent holdout. All 308 sets share the same ten fixed predicates, so they are strongly dependent.

No production filtering rule, no historical source/hash changes, no edits to `main`, no automatic merge. Retain negative findings. Full historical validation and per-rule runtime costs remain separate.

## Exact result — Ubuntu Python 3.12 CI, source SHA 4d70c84a2c04a02874ec4eb7b4fcd605a71ad48a

The read-only union audit passed three focused tests on Ubuntu in [Actions #45329240060](https://github.com/meilin2026dh/pl5/actions/runs/45329240060); Windows is a separate verification gate and must be checked.

| Audit metric | Exact result |
|---|---:|
| All rule conjunctions | 1,024 |
| Nonempty with K <= 100 | 308 |
| **Distinct** candidate masks among those 308 | **92** |
| Empty candidate masks | 68 |
| Number of distinct IDs across the union of the 308 sets | **1,215** |
| Union candidate proportion | 1,215 / 100,000 = 1.215% |
| Retained retrospective targets in union | 0 / 20 |
| Expected retained in union, hypothetical iid uniform | 0.243 / 20 |
| Probability of zero retained, same hypothetical reference | **0.783105** (78.31%) |

Full union bitmap SHA256: `7c08784f030bf4437676fcd109787a43087dda10381288e136d804813ff66e4e`. All 20 frozen retrospective target IDs lie outside this union, independently checked using both bytewise-OR and integer-OR member enumerations.

**Interpretation correction:** 308 individual failures are **not** 308 independent historical tests. The 308 admissible conjunctions collapse to only **92 distinct masks** drawn from the same **1,215 possible IDs**. In the stated hypothetical uniform-ID reference, observing zero union coverage over 20 records has probability 78.31%, so the zero result is unsurprising at this union size. This does not validate the candidate sets or imply any advantage or disadvantage beyond the exact historical observations. The union is a diagnostic counterfactual, not a candidate filter with a K<=100 budget; no union candidate set should be promoted.

No rule or threshold was modified, and no external history was authenticated. Original V3.7.56 evidence and known failure details remain preserved.
