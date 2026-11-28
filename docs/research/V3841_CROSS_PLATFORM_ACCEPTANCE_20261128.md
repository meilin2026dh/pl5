# V3.8.41 — Cross-platform combination optimization verification

Date: 2026-11-28. Source: INTERNAL/AI_AUTHORED.

## Verified evidence

- Certificate commit: 427e48f18208e396e05711fac2c889f060364e2f
- CI gate repair and verified PR head: 5eea7329e44c745709693071fd687dfda9d03774
- Certificate blob: f0b3ba07f2f312acd61ef726753a8b3ce1d47f3e
- Draft PR: https://github.com/meilin2026dh/pl5/pull/34
- Specialized CI: https://github.com/meilin2026dh/pl5/actions/runs/46126909104
- Windows job 140923412087: success; actual certificate output at 08:43:50 UTC.
- Ubuntu job 140923412312: success; actual certificate output at 08:44:03 UTC.
- Application CI: https://github.com/meilin2026dh/pl5/actions/runs/46126909076 — success (pnpm test and pnpm build).

Both specialized job logs explicitly show execution of the V3.8.41 script, not merely the aggregate workflow label. The complete JSON ledgers are identical:

```json
{"empty_queries":1152,"queries":14976,"queries_with_short_cache":5760,"scope_negative_controls":3,"sharpness_cases":18,"source":"INTERNAL/AI_AUTHORED","states":1152,"tied_cost_states":1080}
```

Reproduction:

```sh
node docs/research/experiments/quotient_order_statistic_theorem_v3841.mjs
```

The repaired gate checks exact ledger equality and aborts on any preceding certificate failure. Earlier V3.8.41 aggregate success without explicit script execution is not sufficient evidence. No retry or expanded CI time limit was needed for the verified run.

## Scope

For a fixed eligible set and fixed costs, caching min(k+r, |E|) cheapest distinct IDs suffices to recover the first r surviving cost values after at most k ID exclusions. The explicit-witness cache size is worst-case tight without fallback when |E| >= k+r. The resource-subset dominance construction additionally assumes nonnegative direct coefficient and resource weights. Tied costs do not establish a prescribed ID tie-break. Finite verification uses three IDs and one resource, not all possible resource structures.

No new filtering rule, candidate compression, historical replay coverage, runtime or memory improvement is established here. No historical data or production filter code is changed.

## Branch snapshot before archive

- main: c0e38040ec5f389d6444e64b90e7adc42adfca62
- Draft PR #11: b5687f5e848d1fab567fcd15d8b1eb51d9e3b651
- Draft PR #13: 53425be6a80533c219f097e023209776b3330f24
- Draft PR #34: 5eea7329e44c745709693071fd687dfda9d03774

The independent evaluation gate in Issue #12 remains separate from this internal certificate. This archive itself is not evidence of CI acceptance for its new commit.
