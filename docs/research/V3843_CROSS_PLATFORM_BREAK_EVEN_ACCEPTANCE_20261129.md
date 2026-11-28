# V3.8.43 — combination optimization cache cost accounting: cross-platform execution acceptance

Date: 2026-11-29 (UTC+08:00). Classification: INTERNAL/AI_AUTHORED.

## Scope and evidence

Single task: verify actual execution of the frozen accounting on both platforms, not merely successful workflow status. Source/CI head: `a017b0d91e4af7ef3d6784765b07724d33dbf3e6`.

- [Specialized CI 46171897701](https://github.com/meilin2026dh/pl5/actions/runs/46171897701): Windows job [141061952705](https://github.com/meilin2026dh/pl5/actions/runs/46171897701/job/141061952705), Ubuntu job [141061952907](https://github.com/meilin2026dh/pl5/actions/runs/46171897701/job/141061952907), both success. Step 25 succeeded on each; actual decoded logs contain exactly one standalone execution marker and exactly one JSON result for V3.8.43. Parsed full reports match exactly, including 13 profile rows and five sensitivity rows. Independent sum of every numeric profile field matches aggregate.
- [Application CI 46171897700](https://github.com/meilin2026dh/pl5/actions/runs/46171897700): job 141061952490, frozen dependency install, pnpm test and pnpm build succeeded.
- First-to-last timestamp spans of specialized job logs: Windows 271.604 seconds, Ubuntu 165.749 seconds; both within existing six-minute cap. These are log spans, not algorithm timings.
- Prior execution-coverage gap: source c9534a1dba34242a26adec84f26217e50f6c9b86, specialized run 46166870343 omitted V3.8.43 despite successful status. Earlier Windows cumulative timeout remains part of the audit lineage. This run closes the V3.8.43 execution gap only.

Reproduction from the frozen source:
```sh
node docs/research/experiments/quotient_cache_break_even_v3843.mjs
```

## Matched deterministic ledger

| Metric | Both platforms |
| --- | ---: |
| Ordered combinations | 25740 |
| Cache keys / builds | 366 |
| Disjoint queries | 8190 |
| Full evaluations, baseline / cached (construction included) | 16023 / 5014 |
| Visits, baseline / cached | 21503 / 5176 |
| Lookup tests | 8873 |
| Positive / tied / negative keys | 279 / 13 / 74 |
| Singleton keys / positive singleton keys | 6 / 0 |

| Hypothetical query overhead h | All-cache net | Observed positive-key oracle net | Positive keys |
| ---: | ---: | ---: | ---: |
| 0 | 11009 | 11486 | 279 |
| 1 | 2819 | 3797 | 183 |
| 2 | -5371 | 2160 | 136 |
| 4 | -21751 | 1051 | 67 |
| 8 | -54511 | 405 | 38 |

Under the additive cost model, a key is beneficial iff D > h*q+b, with D evaluation savings (construction evaluations already included), q query count, and b additional non-evaluation build overhead. At b=0 the aggregate break-even h=11009/8190. The observed positive-key oracle uses realized costs and cannot be treated as a prospective dispatch rule. Retain all negative results. No actual timing, memory, candidate set compression or historical retrospective coverage improvement established by this accounting. Frozen development profiles only.

## Repository safeguards

Baseline refs checked: main c0e38040ec5f389d6444e64b90e7adc42adfca62; draft PR #11 head b5687f5e848d1fab567fcd15d8b1eb51d9e3b651; draft PR #13 head 53425be6a80533c219f097e023209776b3330f24; Issue #12 open. PR #34 remains draft. No production filtering rules, historical data, existing checks or compute budgets changed; no merge. This archival document records acceptance of the pinned source, not acceptance of its own future commit.
