# V3.7.31 — exact portfolio engineering, not lottery prediction

## Narrow, testable question

For a **fixed, already defined** inventory of up to 12 Boolean filter masks,
which intersections reach a requested survivor interval, how much work does
their optimal rule execution order require, and which combinations cannot be
improved simultaneously in target-distance, rule count, and scalar checking
cost? The answer is obtained by **exhaustive enumeration**, not a heuristic
fit to winning numbers. This module neither invents new masks nor uses history.

Implementation: `pailie5/constraint_portfolio_v3731.py`.

## Inputs and invariants

Reuse `SearchProblem` from `ga_cs_optimizer_v3715.py` so that rule names,
optional conjunction masks, irrevocable hard mask, `target`,
`min_survivors`, `max_survivors`, `min_active`, and finite universe
stay identical across GA-CS and the exact audit. Only a bounded number of
optional rules is enumerated (at most 12; limit rejects 13+ without
sampling). Static masks mean `True` = **keep**. A fixed hard mask cannot
be disabled by any genome.

There are `2^m` portfolios. For each optional-rule subset `S`:

- `C(S)` is the exact bitset intersection of the hard mask and masks in S.
- `n(S) = popcount(C(S))` counts survivors.
- `W(∅) = 0`; for nonempty S,
  `W(S) = min_{i in S} [W(S\\{i}) + n(S\\{i})]`.
  This Bellman recurrence gives an exact minimum of **scalar candidate-rule
  checks** over all orders, assuming short-circuit evaluation.
- Ties in execution-order cost use deterministic lexical rule indices.
- A feasible S satisfies the supplied minimum active rule count and closed
  interval `min_survivors <= n(S) <= max_survivors`.
- Pareto coordinates for every feasible S: `(|n(S)-target|, |S|, W(S))`,
  **all minimized**. Dominated or duplicate-vector genomes are dropped.
  The deterministic representative minimizes target distance first, then
  evaluation cost, then active rule count, then genome integer.
- Each chosen rule's `recoverable_if_removed` is
  `n(S\\{i})-n(S)`. Zero proves this rule adds no exclusion within
  that specific portfolio. Rule order never changes the final survivors.

The full best-candidate bitmap is SHA256-hashed as fixed-length little-endian
bytes, including leading zero bytes. All identities from 00000 to 99999
remain addressable when universe_size=100000.

## Interpret results cautiously

The optimization **never receives historical winners**. Its engineering
outputs do not report any historical coverage or false-deletion rate.
A separate, frozen time-forward retrospective evaluator is required for
those descriptive metrics; do not tune a genome on its holdout outcomes.
Likewise, scalar evaluation count is *not* measured CPU time. Benchmark
vectorized engines separately before claiming a speedup.

The included deterministic synthetic stress test uses three decimal-position
constraints, whose intersection contains exactly **100 out of 100,000**
identities. This deliberately demonstrates a **99.9% structural reduction**
without presenting the 100 as better candidates, or asserting history/next
period success. Under independent uniform draws, a preselected 100-number
set has exactly **0.1%** inclusion probability. No selection rule here can
turn that deterministic arithmetic into predictive evidence.

## Independent falsification and replay

Run on the current branch:

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_constraint_portfolio_v3731.py tests/test_ga_cs_optimizer_v3715.py
```

The tests check exact feasible subsets against `evaluate_genome`, all
permutations of small portfolios against Bellman-optimal orders, a concrete
case where naive greedy order requires more scalar checks, exact 100k→100
mask arithmetic, immutable hard-mask behavior, redundant-rule diagnostics,
no-feasible conflict handling, and strict exhaustive-size rejection.

**Limits**: The exact Pareto certificate only covers the supplied mask
inventory and uniform per-candidate predicate-check proxy. It cannot
establish that the filters are scientifically useful, stable across time,
independently authenticated or advantageous against a random draw.
No private answers, keys or external graders are used.
