# V3.7.36 — scalable inclusion-minimal static filter pruning

## Bounded engineering question

V3.7.35 proved the **globally minimum-number** equivalent rule subset
by checking all 2^m combinations, which is intentionally bounded to 12
rules. This package answers a distinct, scalable question:

> Given up to 60 frozen Boolean KEEP masks, can we delete redundant
> rules while preserving the **identical final candidate bitmap**,
> and prove that every retained rule is necessary to that exact result?

Answer: yes, using an auditable deterministic one-pass elimination over
the original full conjunction followed by an independent retained-rule
necessity check. The algorithm is polynomial in rule count and bitset
operations. It deliberately **does not** claim a globally minimum number
of rules.

## Algorithm and guarantee

Let H be the immutable hard-mask population, F be the AND of all
optional keep masks, and S initially contain every optional rule.

For each rule index in a supplied fixed permutation, compute the exact
conjunction of all currently kept rules except that index. Remove the
rule **only if** the resulting full candidate bitmap equals F.

Removal cannot create a new opportunity to drop a previously necessary
rule: an identifier excluded uniquely by a necessary rule remains
included when removing that rule, if additional masks are removed
later. One deterministic pass therefore suffices. Recompute the final
bitmap and verify bit-by-bit equality. For each retained rule,
construct a *concrete witness candidate ID* that would reappear if
the rule were deleted, plus the exact number of candidates restored.
Fail closed if any witness is missing.

The default removal order is descending original rule index, providing
deterministic ties. A custom order must be a permutation of all
original rule indices. The hard mask can never be switched off.

**Crucial limitation:** an inclusion-minimal set is not necessarily a
minimum-cardinality set. The included 3-rule counterexample gives an
inclusion-minimal 2-rule result while the exhaustive V3.7.35 oracle
finds a 1-rule exact equivalent. Never use this approximation to claim
global optimality.

## Output and verification

- SHA256 of the raw rule inventory, ordering and immutable hard mask
- SHA256 of the unchanged full candidate bitmap, before/after
- Removed and retained rule indices/names
- Exact candidate count and each retained rule's restoration witness
- Explicit `global_minimum_rule_count_proven=false`
- Explicit absence of historical data or history-coverage evaluation

Run:

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_filter_irredundant_pruning_v3736.py tests/test_filter_equivalent_pruning_v3735.py tests/test_constraint_portfolio_v3731.py
```

The fixtures include 60 independent rules, duplicated rules on the
full 100000-identifier universe, hard-mask interactions, a constructed
global-minimum counterexample, and 30 fixed-seed small-inventory
comparisons against the exact V3.7.35 oracle.

The purpose is to simplify frozen filtering pipelines while retaining
**precisely the same candidate IDs**. No new historical inclusion result
is implied. The scalar runtime cost has not been independently measured,
and reduced rule count does not always minimize execution time.

The next separable work package should quantify exact predicate-check
cost before/after and compare pruning orders under fixed mask
inventories; do not tune with an evaluation window's historical labels.
