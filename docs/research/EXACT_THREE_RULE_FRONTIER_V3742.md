# V3.7.42 — Exact three-rule frontier

## Frozen hypothesis and scope

V3.7.41 certified minimum positive-budget cardinality 3 for the fixed 58-mask inventory. It did not establish whether the existing three-rule witness is unique, nor whether multiple rule triples produce the same candidate set. V3.7.42 examines all C(58,3)=30,856 triples, with no changes to inventory thresholds or source records. Evidence is structural filter engineering only.

## Exact procedure

- Sort rules by name and intersect each unordered triple of immutable integer bitmaps.
- Record the complete retained-count histogram, including empty intersections. Only 1 <= K <= 100 qualifies.
- Preserve every qualifying triple and group them using exact bitmap equality (not merely equal counts or hash equality). Publish the group membership and deterministic SHA256 of each candidate bitmap.
- Separately report exact K=100 portfolios and distinct exact-K candidate sets. These are cardinality-constrained alternatives, not historical quality rankings.
- Bound the inventory to 64 rules and domain to 100000 IDs. No tuning or quota repair.
- Independently compare a small-domain oracle using ordinary set intersections, including duplicated masks, empty intersections and equal-sized distinct sets.

## Replay

From `pl5-cumulative/research_backend`:

```sh
python -m pytest -q tests/test_legacy_filter_matrix_v3740.py
python -m pailie5.legacy_filter_matrix_v3740 --output ../../ci-results/v3742-local.json
```

The existing Windows/Linux Python 3.12 workflow emits the complete JSON evidence. Source commit e927fb101c2a7b7c95b239aa4edeb0a686eff4ff; test commit 3b8e354b42e97e6a5ec151ea460e74622ed47e52. New evidence digest must be recorded separately, never replace earlier evidence. Cross-platform results pending inspection. No authenticated historical coverage, historical exclusion rate or runtime superiority is established. No changes to original historical records or main. Keep PR #13 draft.
