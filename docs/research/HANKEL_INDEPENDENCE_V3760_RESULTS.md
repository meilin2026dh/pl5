# V3.7.60 — Hankel determinant filter: exact independent-contribution acceptance record

Date: 2026-11-24. INTERNAL/AI_AUTHORED.

## Frozen scope and reproducibility

Tested source commit: `a64647c24b91b3ce2a97c6b6a2a3d33a47639d26`.
Implementation commit: `d94557bdb68869a3d480b763015475ad167559b4`.

```sh
python docs/research/experiments/hankel_independence_v3760.py
```

For a five-digit combination (a,b,c,d,e), the sole added binary rule is
D>0, with D=ace+2bcd-ad²-b²e-c³. The determinant oracle enumerates the six
signed permutations independently of this expression. The full domain
and reversal invariant are checked for every ID. The legacy mask manifest
is checked against its frozen digest. All 68 baseline mask hashes and
the new mask digest are emitted in the machine-readable CI output.

## Exact full-domain results

| Measure | Value |
|---|---:|
| Domain | 100000 |
| D>0 standalone retained K | 15053 |
| Standalone compression | 84.947% |
| D=0 | 928 |
| D<0 | 84019 |
| Distinct integer D | 1468 |
| Baseline rule count | 68 |
| Baseline signature classes | 92906 |
| Refined signature classes | 93568 |
| Baseline classes split | 662 |
| Baseline indistinguishable unordered pairs | 41102 |
| Newly separated unordered pairs | 7311 |
| Remaining indistinguishable unordered pairs | 33791 |
| Relative reduction of baseline indistinguishable pairs | 17.7875% |
| Ten-rule atomic partition classes | 319 |
| Eleven-rule atomic partition classes | 580 |
| Ten-rule union of atoms individually satisfying K≤100 | 5082 |
| Eleven-rule union of atoms individually satisfying K≤100 | 9230 |

The cross-product count within each existing signature class is exact:
if that class contains p combinations satisfying D>0 and q combinations
not satisfying it, the new rule separates p*q previously indistinguishable
unordered pairs. Summing gives 7311, independently checked against the
difference in within-class pair totals, 41102−33791. Thus this rule is
not expressible as any Boolean function of the fixed 68 binary outputs.
This is a proof of incremental static distinguishability, not a
statistical independence claim or a measure of unique exclusion in a
particular AND portfolio. No threshold or rule choice was fitted.

The small-atom union increases by 4148 IDs; that diagnostic union is
NOT one filter meeting K≤100. The standalone rule does not meet K≤100.
Historical backtracking coverage and historical false exclusion have not
been measured in this task. No practical coverage improvement is
established. No original history or independent test material was read
or modified.

## CI acceptance

[Targeted Windows and Ubuntu Python 3.12 CI](https://github.com/meilin2026dh/pl5/actions/runs/45335417606)
passed three deterministic tests on each platform. The complete
`V3760_HANKEL_JSON` payloads are byte-identical (8692 characters).
[Application CI](https://github.com/meilin2026dh/pl5/actions/runs/45335417457)
also passed on the tested source commit. The earlier V3.7.59 application
CI timeout is retained in its own record; no general reliability claim
is made. Acceptance here is limited to the tested static rule and
independent-contribution proof, not a new full-project acceptance.

## Repository review

main: `c0e38040ec5f389d6444e64b90e7adc42adfca62`, unchanged.
Draft PR #11 head `b5687f5e848d1fab567fcd15d8b1eb51d9e3b651`: five
associated PR workflows passed. Draft PR #13 head
`53425be6a80533c219f097e023209776b3330f24`: ten associated PR workflows
passed. Issue #12 remains open; independently sourced validation gates
remain outstanding. No source history, main, or merge operations were
performed in this task.

Decision: retain D>0 as a non-redundant experimental static filter.
Further promotion requires separate frozen-rule coverage and cost
comparison; the static contribution alone does not warrant promotion.
