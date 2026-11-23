# V3.7.37 — DSC digit-structure operators: exact enumeration and incremental filtering audit

## Scope and scientific question

This is the first PL5-DSC research work package: define a small, deterministic
library of **five-digit structural filtering operators** and determine exactly
what each contributes beyond a frozen baseline filter. All 100,000 candidate
identities are enumerated; **no historical records are opened or fitted**.
The objective is filter-algorithm explainability and redundancy accounting,
not a long-sequence randomness assessment. Five digits cannot provide
meaningful NIST SP 800-22 long-stream significance-test results.

## Fixed mathematical features

Write the digits as d0,...,d4. For j=0,...,3 define
Δj=(d(j+1)-dj) mod 10. The three predeclared features are:

- `mod10_curvature_zeros`: number of j=0,1,2 for which
  (Δ(j+1)-Δj) mod 10 equals zero. Value 3 identifies a complete modular
  arithmetic progression, including a constant string and wraparound cases.
- `mod10_delta_distinct`: number of distinct values among the four
  cyclic differences. Values lie in 1..4; low diversity describes a
  restricted local pattern, not a probability model.
- `lag2_matches`: number of equal digit pairs (d0,d2), (d1,d3),
  (d2,d4). Value 3 identifies an exact two-position repeat.

Each property is checked over all `00000..99999`, preserving leading
zeros. Feature tables are cached read-only NumPy arrays. A registered
filter specifies the feature, comparator (eq/le/ge), and integer
threshold. Compiled masks use **True=KEEP** with exact little-endian
identity bit order. No parameters are trained in this work package.

## Five developer-authored filters and exact counting

The frozen rule inventory contains modular progression, exact lag-2
repeat, low difference diversity, near lag-2 repeat, and a deliberate
duplicate modular progression rule. The duplicate is a negative control
for marginal contribution. The first four operators are *candidate
research hypotheses*, not automatically useful exclusion criteria.

Before touching historical evidence, we can establish exact checks:

- 100 out of 100,000 strings are full modular arithmetic progressions
  (10 possible starting digits times 10 possible steps).
- 100 out of 100,000 satisfy all three lag-2 equalities
  (the first two digits determine the remaining three).
- The two preceding families intersect in exactly 10 constant strings.
- Exactly 6,400 strings have ≤2 distinct modular adjacent differences:
  10 starting digits × [10 single-symbol difference sequences +
  C(10,2)(2⁴−2) sequences that use both distinct symbols].

These numbers describe the whole finite universe, not historical
statistics. They are useful independent arithmetic oracles for the code.

## Marginal contribution against existing filters

A frozen illustrative baseline uses pre-existing indicators:
`10 <= sum <= 35` and `span >= 3`. This illustrates the API, and
has **not** been chosen based on observed historical performance.

For a new rule R with excluded set E and baseline keep set B,
the exact **new exclusions** are `|B∩E|`. The overlap with exclusions
already made by the baseline is `|E∩(U\B)|`. After applying earlier
new rules, the additional marginal amount is
`|B_after_previous∩E|`. The module reports these quantities
separately for every rule and checks complete count conservation.
The final candidate mask and baseline mask are SHA256-bound.

The final candidate set does not change when a duplicate exclusion
rule is appended. However, the attribution of marginal exclusions
among different rules **depends on their execution order**, so an
ordered audit must not be read as order-invariant rule importance.
Existing V3.7.34 Shapley analysis addresses that complementary
question.

## Replay and next gate

Source: `pailie5/digit_structure_v3737.py`
Tests: `tests/test_digit_structure_v3737.py`

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_digit_structure_v3737.py tests/test_filter_interactions_v3734.py
```

No empirical historical containment has been measured. The next
separate work package can wrap these masks in the existing
`SearchProblem` and test a fixed same-budget frontier. Only afterward,
with independent and source-authenticated history and an explicitly
frozen rule set, should one attempt a strictly chronological
retrospective retention audit. Never select thresholds on the
evaluation window.
