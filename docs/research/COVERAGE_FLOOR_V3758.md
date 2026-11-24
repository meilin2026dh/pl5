# V3.7.58 — Exact candidate-budget floor for historical coverage

## One bounded, falsifiable investigation
V3.7.56/57 proved 308 nonempty fixed-rule AND subsets satisfy K<=100 but fail to retain any of 20 crosschecked retrospective records. They share just 1,215 candidate IDs. The next highest-value question is: **what is the minimum candidate-set cardinality K required for any subset of the same frozen ten rules to contain each historical record?** This is not a search for a best performing subset, and must not be used to select one from this retrospective window.

## Exact theorem
For a target identity t define S(t) as the indices of frozen predicates that retain it. Any AND subset that retains t must be contained in S(t). Conjunction is monotone in rule inclusion; consequently the **smallest K among all 1,024 subsets that still retain t is achieved by S(t)**, though several subsets may tie. The executable compares this theorem with an **independent exhaustive enumeration of all 1,024 subsets for every one of 20 evaluation identities**. Any difference blocks acceptance. No thresholds or old rules change.

## Frozen protocol
- Ten existing, predeclared binary predicates and 1,024 exact full-domain AND bitmaps (source V3.7.56).
- Freeze the union of all nonempty subsets under each *predeclared* budget K<=100,500,1000,5000,10000,20000,50000,100000 before opening any target record; track union K, exact mask digest, and number of eligible subsets.
- Use the same original immutable byte-hash-verified primary 51-row transcription and crosschecked 20-record terminal interval, issues 26275..26294. The first 31 rows precede the evaluation window. Do not edit raw bytes or digests.
- For each target, disclose the minimal attainable K and exactly which frozen predicates it meets. Recheck per-target minimum K against all 1,024 AND subsets and each predeclared cap against that cap's frozen union.
- The cap/frontier is **retrospective descriptive evidence**, not a prospective selection procedure. Do not choose or optimize a new rule based on the 20 outcomes.

## Reproduce and audit
```sh
python docs/research/experiments/coverage_floor_v3758.py
```
Three unittest tests cover exact all-subsets/cap conservation and the existing K<=100 regression, independent toy-domain minimum-K proof, and deterministic replay. Ubuntu/Windows Python 3.12 CI is a separate required acceptance gate. The complete per-target JSON is printed to CI logs with membership certificates and all cap union SHA256 values.

## Limitations
- The historical transcription rows lack independently authenticated archived publisher pages and independently witnessed precommitment.
- All ten predicates have been through research development, and the same retrospective outcomes may have influenced prior hypotheses; this is not a fresh independent holdout.
- Even if some cap on this panel covers more targets than another, no model selection, future performance or statistical superiority follows.
- The cap K=100 is an engineering target, not a threshold to revise to fit the panel. Zero-size subsets are excluded as invalid.
- No new production rule, no original-data/hash changes, no main changes, no merge. Preserve negative outcomes.
