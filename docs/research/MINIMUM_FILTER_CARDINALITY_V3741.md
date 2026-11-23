# PL5 V3.7.41: exact minimum-rule-count certificate for the frozen filter library

## One falsifiable question

For the full 00000–99999 domain and the **58 registered static keep masks** in
the V3.7.40 unified matrix, does the existing greedy three-rule combination
with nonempty K=100 candidates use the **fewest Boolean-AND rules** possible
in this exact frozen inventory?

This is a structural cardinality question only. It is neither a claim of
minimum execution time nor an assessment of chronological historical coverage.

## Exact exhaustive method

The new audit function `_minimum_cardinality_certificate` takes exactly the
same ordered, frozen mask inventory and the independently produced greedy
witness. It requires each candidate mask to be a finite-domain integer bitmap,
each name to be unique and the witness to retain **1..100** candidates.

For a three-rule witness, it enumerates every smaller subset, namely:

- zero rules: `C(58,0) = 1`;
- one rule: `C(58,1) = 58`;
- two rules: `C(58,2) = 1653`.

Thus **1712 subsets are checked**. Each intersection is computed exactly using
integer bitmap AND and `bit_count()`; an empty intersection does **not** meet
the positive-candidate budget. Each subset cardinality reports total, empty,
nonempty and minimum positive retained count. If any smaller subset retains
1..100 candidates, the function records a named concrete counterexample and
explicitly rejects minimality. The full three-rule witness is separately
recomputed, and its count plus byte-fingerprint must agree with the existing
greedy engine. The exact certificate is embedded in the V3.7.40 report
as `minimum_rule_cardinality_certificate`.

A certificate of minimum rule **count** is valid only within this exact
declared family of 58 masks and the fixed `K <= 100, K > 0` rule.
It cannot show that the selected constraints are meaningful for independent
data, or that their order minimizes compute time.

## Independent adversarial regression

Small-domain test fixtures independently establish the following:
three rules may be necessary; an unused duplicate/redundant rule must
not obscure a two-rule counterexample; zero-size intersections must
never be counted as successful compression; malformed, duplicate or
out-of-range masks fail closed. A full-domain regression also checks the
exact subset denominator, independent greedy-mask hash agreement and
the expected three-rule certificate.

## Reproduction and evidence gates

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_legacy_filter_matrix_v3740.py
python -m pailie5.legacy_filter_matrix_v3740 --output ../../ci-results/v3741-proof-local.json
```

The report refuses to overwrite evidence. The Linux/Windows Python 3.12
dedicated workflow is `.github/workflows/pl5-legacy-allmethods-v3740.yml`;
the separate full clean-machine Python/history replay must also pass.
A newly generated report has a new code/source fingerprint and JSON checksum;
prior V3.7.40 evidence and the historical input digests remain unmodified.

**Limit:** This exact mathematical certificate uses frozen filters only.
Historical time-forward coverage, actual historical false-exclusion rate and
any authentic historical source provenance remain unverified in this package.
No source data, original digests, private inputs, or main branch are modified.
