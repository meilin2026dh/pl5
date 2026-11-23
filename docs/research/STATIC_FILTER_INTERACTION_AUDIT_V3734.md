# V3.7.34 — static filter interactions, redundancy and exact attribution

**Research question:** For a frozen inventory of Boolean *keep* masks,
which rules duplicate exclusions, which exclusions are unique, how large
are pairwise overlaps, and how much of the total elimination can be
attributed to each rule *without choosing an arbitrary execution order*?

This is a filter-engineering audit; there are **no lottery draw data** or
historical labels in the code.

## Proven invariant: static AND filters cannot create positive exclusion synergy

Let H be the hard-mask population and let R_i ⊆ H be the candidate IDs
excluded by optional rule i. For any subset S of selected rules, the
excluded set is ∪(R_i for i∈S). Thus f(S)=|∪R_i| is monotone and
**submodular**:

f(S∪{i})-f(S) ≥ f(T∪{i})-f(T) for S⊆T and i∉T.

In particular, f({i,j})=f({i})+f({j})-|R_i∩R_j|. A claim of *more
than additive* additional exclusions from a static conjunction would
violate set-union arithmetic. More rules may introduce distinct
exclusions, but any overlap reduces incremental benefit. No empirical
data, statistical test or numerical search can overturn this invariant
under the stated static-mask assumptions.

The module independently verifies all **2-dimensional faces** of the
subset lattice, sufficient to check every immediate diminishing-return
inequality, and fails closed on a negative gap. This proof **does not**
cover conditional filters whose mask changes with prior decisions, or
rules re-fitted on newly revealed data.

## Exact metrics

- Full bitset intersections for all 2^m portfolios, capped at m≤12
  and universe≤100,000; original masks remain unchanged.
- Pairwise exclusion counts and overlaps, directional incremental
  exclusions, exact duplicate-exclusion identification, and rational
  overlap/union Jaccard values (no floating precision ambiguity).
- **Exact Shapley attribution** of total excluded identities: average
  marginal exclusions over every possible rule ordering, expressed as
  reduced rational numerators/denominators, with exact conservation
  check ∑Shapley_i = f(all).
- SHA256 of the frozen raw masks, names, ordering, hard-mask and universe.
- Explicit classification as `historical_coverage_measured=false`,
  `forecasting_performed=false`, `future_advantage_claim=false`.

Shapley values distribute **overlapping exclusions** fairly across
rules for engineering diagnosis; they are not evidence of superiority,
causal influence or historical retained outcomes. Rule order can
change scalar evaluation cost but not the final static AND mask.

## Replay

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_filter_interactions_v3734.py tests/test_constraint_portfolio_v3731.py
```

The tests include independent three-rule permutation enumeration for
Shapley fractions, duplicates, zero-overlap exclusions, hard masks,
complete-removal rules, source hash sensitivity, the full 100,000-space
to 100 synthetic structural intersection, and strict 12-rule bound.

**Next research step:** Use these exact overlap diagnostics as an
audit instrument to identify redundant rules in a frozen, externally
authenticated rule inventory. Only *then* evaluate historical containment
on untouched forward windows, without using those windows to choose
rules. A historical high retention rate is descriptive, not predictive.
