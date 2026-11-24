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
