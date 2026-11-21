# GA-CS Optimization Engineering Protocol (V3.7.15)

## Scope
A 20-bit optional condition genome indexes 20 frozen 100,000-bit PL5 masks generated from existing `BasicConstraint` definitions. A separate mandatory hard mask is always applied and cannot be mutated. The enabled rules are strict conjunctions; there is no fuzzy membership or lottery inference.

## Fitness and safety
Given retained count `n` and desired target `T`, score feasible candidates as `-|ln((n+1)/(T+1))| - 0.014 × active_rule_count`; violating the allowed interval or minimum enabled-rule count receives a stronger negative penalty. Feasibility is always compared before score. This trades off engineering compression and rule count, **not coverage of future drawings**. Every candidate evaluation counts toward a fixed oracle-call budget even when it repeats.

## Six competing methods
- Random search;
- greedy local bit flip with periodic restart;
- simulated annealing;
- GA with tournament, uniform crossover, mutation, bounded elite pool;
- CS with Mantegna beta=1.5 Lévy-flight bit flips and 12% random nest abandonment;
- GA-CS with 30% GA evaluations then 70% CS, preserving elite population.

## Preregistered experiments
- Rule pool: existing `benchmark_high_throughput_v3714._rules()` of 20 deterministic static rules.
- Frozen universe: 00000 through 99999.
- Strict equal budget: 300 objective evaluations per method per seed.
- Eight original seeds 0..7; target 36,000, admissible 28,000–42,000; minimum 2 active rules.
- Separate 100-ticket feasibility-negative control: target 100, allowed 1..100, same seeds/evaluations.
- Follow-up robustness (exploratory, not confirmatory): 12 unseen optimizer seeds 100..111 and three targets 32,000 / 36,000 / 40,000.
- Outputs and runtime per method recorded, original NumPy `apply_basic_filters` used to check **exact ticket membership**, not merely set cardinality.

## Boundaries
No verified real drawing history is available in this experiment. No sample-out predictive claim is possible. If a later version optimizes with verified real history, use time-forward train/calibration/test partitions and freeze algorithm/parameters before final holdout. Do not select hyperparameters based on that holdout. For hard funding caps, an unattainable target must return infeasible.
