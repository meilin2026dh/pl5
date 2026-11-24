# V3.7.35 — Exact equivalence-preserving simplification of filter combinations

## Engineering question

Given up to twelve fixed Boolean KEEP rules (and an immutable hard-mask
population), can we delete optional rules while **preserving every member**
of the final candidate set rather than merely preserving the count?

This is filter-algorithm engineering. It does not use historical records.

## Exact method

For m rules, enumerate all 2^m subsets, calculate each subset's full AND
bitset under the immutable hard mask, then compare to the AND of **all m**
rules. Only subsets with **bit-for-bit identical** candidate masks qualify.
Select the subset with (1) fewest optional rules, (2) lowest exact minimum
scalar short-circuit checks over all rule orders (Bellman DP inherited from
V3.7.31), (3) smallest genome as deterministic tie-break.

Report all equivalent-subset counts, inclusion-minimal core count,
rules essential across *all* equivalent subsets, original versus simplified
scalar work, and SHA256 of the final candidate bitset. Alternative minimal
cores are not assumed unique, and an individual rule may appear dispensable
only because another equivalent rule remains.

Exactly matching the candidate mask means retaining its existing historical
membership characteristics without any new historical fitting, but it is
not a new coverage result. Removing redundant rules does not alter the set.

## Test commands

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_filter_equivalent_pruning_v3735.py tests/test_filter_interactions_v3734.py tests/test_constraint_portfolio_v3731.py
```

The independent tests enumerate all small subsets and all rule permutations
to verify the lexicographic winner and minimum check count. Other cases
cover duplicate masks, unique necessary rules, immutable hard masks, and
a 100,000-identity structural example retaining exactly 100 identities.
All fixtures are INTERNAL and developer authored.

## Limits

The complete proof applies only to static rules within the declared
universe. Conditional or history-adapted rules need an explicit composition
model. The scalar check proxy is not elapsed CPU time. No historical
coverage evaluation is performed here. No file containing unreleased data
is needed, and no accepted historical digest is changed.

A future work package may integrate rule simplification as a
semantics-preserving preprocessing step before larger portfolio search,
provided the original and simplified candidate bitmaps are compared and
their full provenance recorded.
