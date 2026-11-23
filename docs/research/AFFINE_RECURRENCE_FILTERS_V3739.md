# PL5 V3.7.39 — exact affine-recurrence filtering: constructive compression certificate

## Question and falsification

The V3.7.38 frozen structural rules retained 87,404 of 100,000 candidate identities, so their conjunction did not meet the 100-ID engineering limit. This package asks a deliberately narrower mathematical question: **can a new, explicit, verifiable modular relation grammar create a 100-ID subset without threshold fitting or opaque optimizer output?**

Let the five digits be d0,d1,d2,d3,d4. Fix three rules:

- d2 ≡ d0+d1 (mod 10)
- d3 ≡ d1+d2 (mod 10)
- d4 ≡ d2+d3 (mod 10)

These are independently defined Boolean KEEP masks. No historical records, parameters or external randomness are used.

## Exact constructive proof

Choose the first two digits freely: there are 10×10=100 choices.
The three displayed constraints uniquely determine the remaining three digits by modular arithmetic. Each initial pair therefore produces a unique five-digit identity satisfying all rules, and **every** identity satisfying all rules arises this way. Hence exactly 100 out of the 100,000 identities remain.

The full-domain census confirms the sequential retained counts **10,000 → 1,000 → 100**, while an independent generator enumerates all 100 free two-digit seeds and verifies bit-by-bit equality. The V3.7.31 exhaustive eight-subset oracle additionally confirms that only the full three-rule conjunction reaches a 1..100 retained interval with these masks. The V3.7.34 static rule interaction engine supplies further reproducibility checks and exact attribution.

The existing illustrative sum/span hard mask is tested *separately* for intersection and cannot increase the 100 identities. Its overlap is reported explicitly, not silently substituted as a newly discovered engineering advantage.

## Interpretation of the result

This is a **constructive structural compression result**, not evidence of a particularly *useful* filtering method. A designer can trivially create many arbitrary constraint systems that leave 100 identities: hitting a size target alone is weak evidence of research quality. This package is valuable primarily as an exact proof-of-capability, a source of test oracles for future operator combinators, and a counterexample to interpreting strong compression as historical effectiveness.

No historical retention is computed; the large compression ratio is achieved by construction, and the arbitrary recurrence grammar has no empirical superiority status. Next work must compare structure-grammar complexity, independent rule contribution and the historical retained proportion on strictly frozen evaluation windows. Do not adjust this grammar after reviewing those windows.

## Replay

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_affine_recurrence_filters_v3739.py tests/test_digit_structure_v3737.py tests/test_constraint_portfolio_v3731.py tests/test_filter_interactions_v3734.py
```

Source: `pailie5/affine_recurrence_filters_v3739.py`.

All source commitments, identities and counts must remain reproducible. The existing historical dataset and `main` are unchanged.
