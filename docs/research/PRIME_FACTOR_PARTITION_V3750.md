# V3.7.50 — Prime-factor structural partition audit

## Frozen engineering hypothesis
Three number-theoretic descriptors of integer-encoded IDs—distinct prime factor count (omega), prime factor count with multiplicity (big omega), and squarefree flag—may partition the 100000-element domain in a way not solely determined by last digit or modulo 7. This is a **structural independence check only**. The entire existing rule inventory is NOT compared. No threshold for exclusion is selected.

## Definitions
- Integers 00000..99999 map to 0..99999, preserving the original finite candidate domain.
- 0 has a dedicated sentinel (-1,-1,-1); 1 has (0,0,1). These are not assertions about mathematical factorization of zero.
- For n >= 2, omega(n) counts distinct prime divisors, big omega(n) counts divisors including multiplicities, squarefree(n) is 1 iff every exponent is 1.
- Existing V3.7.39 recurrence fixture: 100 IDs from two free decimal digits and three fixed recurrence steps. INTERNAL/AI_AUTHORED only.

## Exact local results
| Descriptor | Number of IDs in the 100-member fixture | Special detail |
|---|---|---|
| omega distinct | sentinel:1, 1:12, 2:30, 3:43, 4:12, 5:2 | no other positive categories represented |
| big omega multiplicity | sentinel:1, 1:12, 2:16, 3:30, 4:21, 5:8, 6:5, 7:2, 8:2, 9:2, 10:1 | all other categories zero |
| squarefree | sentinel:1, non-squarefree:38, squarefree:61 | complete 100-member partition |

Each descriptor varies inside at least one fixed last-digit class and at least one fixed mod-7 class, proving that the feature is **not a function of either single existing descriptor**. This does not prove independence from combinations of existing filters. Full-domain distribution counts and a SHA256 of all 100000 feature triples are emitted by the program.

## Validation and reproduction
```sh
python docs/research/experiments/prime_factor_partition_v3750.py
```
Three self-contained stdlib unittest cases check: sieve SPF versus independently written trial division for all 100000 IDs; an independently derived closed-form recurrence formula on all 100 fixture IDs; conservation, replay stability, and nontrivial partitions conditional on last digit and mod 7. Verified in local Python runtime. Full domain feature table SHA256: `7d3f15f978295707a497d38085bc359b055c2bdb0f4f16ca60039dc766b7809c`.

## Limitations and negative result
No factor-category exclusion choice has been frozen or evaluated. A partition is not evidence of useful filtering. Full-library redundancy/equivalence, historical time-forward coverage and deletion rate, actual execution cost, and equal-budget baseline comparison remain unmeasured. No new production filtering rule is justified. Test data are INTERNAL/AI_AUTHORED; no third-party blind test. CI status must be checked separately for Windows and Ubuntu, and successful focused tests do not constitute complete acceptance. No main, stored history, data hashes or existing source modules changed.
