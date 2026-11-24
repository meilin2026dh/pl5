# V3.7.49 — exact modular residue partition (INTERNAL/AI_AUTHORED)

## Frozen, falsifiable question
Do congruence classes of the integer encoding of the full five-digit domain yield a nontrivial, nonredundant structural partition of the preexisting V3.7.39 100-member recurrence fixture? This bounded audit computes **exact counts**, not a historical filtering benefit. Residue 0 is a fixed diagnostic label, **not** an optimized exclusion threshold. No adaptive choices, no external records.

## Reproduction
```sh
python docs/research/experiments/residue_partition_v3749.py
```
The self-contained standard-library implementation has 3 deterministic unittest cases: independent full-domain enumeration, independent closed-form digit-construction oracle, and repeatability/conservation. No source data, historical digest or production filter is changed.

## Locally verified arithmetic (100000 total, 100 recurrence members)
| p | Exact recurrence counts for residues 0..p-1 | residue 0 retained | marginal excluded by residue 0 |
|---|---|---:|---:|
| 2 | 50,50 | 50 | 50 |
| 3 | 36,32,32 | 36 | 64 |
| 5 | 20,20,20,20,20 | 20 | 80 |
| 7 | 13,10,15,19,15,13,15 | 13 | 87 |
| 11 | 9,8,9,12,6,10,10,8,8,11,9 | 9 | 91 |
| 13 | 8,6,7,8,7,8,8,7,7,11,6,10,7 | 8 | 92 |

Expected exact full-domain count for residue r modulo p is floor(100000/p) plus one when r < 100000 mod p. No probabilistic approximation needed. A selected residue class can trivially compress the 100-member set further, but **that alone is not rule quality**. Modulo 2 and 5 are determined only by the final digit; their re-expression offers no new information if corresponding positional features are already available.

## Negative finding and decision
Exact residue-count partitions exist, but this audit **does not establish independent value versus the full existing rule inventory**, historical retention, or a useful filtering threshold. Do not promote any residue rule to production or optimize over observed windows. A future predeclared experiment would need frozen class choice, complete-inventory equivalence/redundancy checking, cost measurement and time-forward historical containment against an equal-budget control.

## Boundaries
Only INTERNAL/AI_AUTHORED fixed mathematical inputs. No third-party independent test; no historical data read; no timestamp attestation, no claim about historical coverage or error rate. The mathematical result does not require or use properties of zeta zeros. Windows/Linux CI is a separate gate; local tests alone are insufficient for cross-platform acceptance. No main change, no merge.
