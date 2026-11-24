# V3.7.32 — Equal-evaluation-budget search versus exact filter-combination oracle

## One falsifiable question

For a **frozen list of Boolean keep masks**, can the existing V3.7.15 GA-CS
combination search find the same best scalar objective as exhaustive search
under a strictly counted limit of candidate evaluations, and how often does
random combination search do the same with **the identical budget**?

This is *optimization research*, not number forecasting. It never reads
historical draws or uses winners as a search fitness signal.

## Artifact and replay

- Code: `pailie5/filter_search_oracle_v3732.py`
- Tests: `tests/test_filter_search_oracle_v3732.py`
- Existing frozen optimizers: `pailie5/ga_cs_optimizer_v3715.py`
- Existing three-dimensional exact Pareto engine:
  `pailie5/constraint_portfolio_v3731.py`

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_filter_search_oracle_v3732.py tests/test_constraint_portfolio_v3731.py tests/test_ga_cs_optimizer_v3715.py
```

```python
from pailie5.filter_search_oracle_v3732 import compare_search_to_exact_oracle
result = compare_search_to_exact_oracle(frozen_search_problem,
                                        seeds=(373201, 373202, 373203),
                                        evaluations=48)
```

The deterministic inventory manifest SHA256 binds mask hashes, named rules,
hard-mask hash, universe dimensions, feasibility constraints and objective
weight. The exact oracle enumerates all `2^m` genomes for `m <= 12`,
with one `evaluate_genome` per genome and deterministic tie priority.
Both bounded searches (random, GA-CS) consume exactly `evaluations`
calls per seed. Repeated proposals still count. All seeds and method results,
including failures to reach the oracle, must be retained.

The oracle uses V3.7.15 **same scalar fitness** as the bounded searches, not
the distinct V3.7.31 Pareto metric. Reporting that GA-CS found the optimum
is not sufficient to claim it is more efficient than random: show comparative
per-seed optimum attainment and objective gaps with all seeds retained.
Exhaustive `2^m` calls are separately charged, and equal objective calls do
not imply equal CPU or wall-clock cost.

## Scientific interpretation

The code has only synthetic/internal tests so far. No new public historical
retrospective coverage study, no private/unknown evaluation, no empirical
advantage and no production recommendation is asserted. Under uniform iid
draws, the probability of including an independent outcome in a fixed set
of K combinations stays K/100000. Historical retention and actual computation
speed are separate questions.

**Next independent work package** (not executed here): freeze a rule inventory,
run a bounded multi-instance benchmark with fixed seeds, uniformly report all
negative and positive comparisons, then assess Pareto/frontier tradeoffs.
Only after that should history be introduced to a separately preregistered
past-only evaluator. Do not tune any rule using its held-out history.
