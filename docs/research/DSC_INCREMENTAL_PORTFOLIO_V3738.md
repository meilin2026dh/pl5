# V3.7.38 — DSC structural filters versus conventional baseline: exact contribution

## One bounded question

On the complete 100,000-identity five-digit universe, how much genuinely
new exclusion does each V3.7.37 structural operator add beyond a frozen
sum/span conventional baseline, and can the combined rule list be reduced
without changing a single retained candidate?

This uses the **existing exact** V3.7.31 subset and frontier census,
V3.7.34 pairwise overlap and Shapley allocation, and V3.7.35 exact
equivalent-subset pruning. It does **not** invent another optimizer,
alter the prior rule definitions or fit against historical records.

## Frozen inputs and outputs

The baseline keep mask is exactly `10 <= sum <= 35` AND
`span >= 3`; the five static V3.7.37 structural rules retain their
fixed definitions and order, including the deliberate duplicate control.
All hashes use 100,000 numeric identities in little-endian bit order.

Outputs include the baseline candidate count and SHA256, full-rule
candidate count and SHA256, individual standalone elimination counts,
overlap with conventional exclusions, marginal eliminations in
predeclared order, pairwise overlap, order-independent Shapley
attribution, exact 2^5 subset Pareto frontier and minimum-cardinality
bitmap-equivalent rule family.

The `max_candidates=100` cap is a hard engineering condition. If no
subset of these **particular** frozen rules can meet the target,
`best_under_cap` is `null`; it is **not** repaired with arbitrary
additional exclusions. A separately constructed `max_candidates=100000`
audit can cross-check structural arithmetic, but must not be presented
as satisfying the 100-candidate target.

## Exact 100-ID cap result (frozen V3.7.37 inventory)

The full 100000-identity census establishes a negative result for this
particular baseline and five optional rules. The fixed baseline retains
**94890** identities. Marginal additional exclusions in the declared
rule order are **90, 40, 5728, 1628, and 0**, respectively. All rules
together exclude **7486** beyond baseline, retaining **87404** identities.

Since applying every rule is the strongest possible conjunction, no
subset of the five can retain fewer than **87404**. Consequently **none
of the 32 subsets can meet the requested 100-ID cap**. The result is
an exact mathematical infeasibility certificate, not a search failure
or an invitation to silently add exclusions.

Exact bitmap-equivalent pruning independently shows that only two
rules are needed to retain those same 87404 identities:
`exclude_low_delta_diversity` and `exclude_near_period2`
(genome `0b01100`). The other three rules are redundant **for the full
conjunction under the stated hard baseline**, although Shapley credit
for a redundant rule can be positive when averaged over rule orderings.
Scalar check savings refer to a cost proxy, not measured wall time.

This result applies only to the fixed inventory and says nothing about
different, independently specified rule families. The full-inventory
retention reference is exactly **87404/100000**; no historical time-forward
coverage was measured.

## Verification

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_dsc_portfolio_audit_v3738.py tests/test_digit_structure_v3737.py tests/test_constraint_portfolio_v3731.py tests/test_filter_interactions_v3734.py tests/test_filter_equivalent_pruning_v3735.py
```

New module: `pailie5/dsc_portfolio_audit_v3738.py`

The suite checks 32 possible DSC rule subsets under identical frozen
constraints, independently re-scores every subset against the
pre-existing `evaluate_genome` oracle, and crosschecks three
independent full-bitmap descriptions, exact count conservation, cap
refusal and duplicate-rule zero marginal contribution. A separate
fixed-count oracle checks 94890/87404/7486, the full 32-subset
minimum, the unique two-rule smallest equivalent core and exact
Shapley conservation.

**This module does not read any historical outcome data or establish any
historical coverage.** It produces exact structural measurements only.
Improvement in independent contribution is not automatically improvement
in operational value; evaluation time and retained-history checks remain
separate requirements. Future evaluation should freeze source rule
definitions and historical time-window boundaries before data access,
report every window including negative results, and never use the
evaluation period to adjust thresholds.
