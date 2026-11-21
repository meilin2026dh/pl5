# V3.7.6 Adaptive Scientific Method Design

## Intent
Advance PL5 from choosing a prebuilt experiment to selecting and running controlled *methodological interventions* when a scientific question remains unresolved. Reuse V3.7.5's question ledger, V3.7.3's frozen AST search, V3.7.2's independent operator evaluator. This is deterministic, bounded, offline hypothesis-testing software; no LLM, self-modification or claims of a predictive edge.

## Options considered
1. **Chosen:** isolated hypothesis-conditioned, two-arm intervention studies and append-only evidence records. Low integration risk and preserves historical research.
2. Modify V3.7.4 controller directly to synthesize arbitrary Python experiments. Rejected: unsafe arbitrary execution, poor auditability, and potential corruption of old cycles.
3. Reuse unchanged experiments but reword the question as a new method. Rejected: no real intervention, cannot distinguish explanations.

## Research protocol
- Consume read-only V3.7.5 registry and completed cycle evidence; prioritize an unresolved `needs_new_method` question.
- Design one of three intervention classes for each new, independent synthetic task: **more training cells**, **richer expression tree capacity**, **larger search budget**. Each study compares baseline vs challenge on precisely the same 20 held-out input pairs. Train 60 or 80 of the other 80 available cells; unused cells are not labels for fitting.
- Schedule an independent random-table negative control every fourth study (cannot be displaced). Reserve test coordinates and lock method, seed, budgets and data split before obtaining any labels for fitting. Freeze and serialize *both* fitted operators before reading holdout labels into evaluation.
- Persist SHA-256 of plans and operator identities; reject altered plans, mismatched config and incomplete artifacts. Do not tamper with or rewrite historical V3.7.5 files. Persist evidence with denominator, cost, independent split, and distinction between exploratory results and validated science.
- Adaptive selection of untried method classes; never reuse held-out cells as training in the same study. Old heldouts can motivate *future fresh* studies but cannot be used for formal tests.
- The research stops after the requested finite number of studies, if resource caps reached, or on a programming/data-integrity error. No unattended background execution.

## Non-goals
Not a general autonomous scientist, no arbitrary executable code generation, no production betting filter, no statistical significance from repeated adaptive synthetic trials, no changes to original GitHub repo or Windows machine.

## Verification
TDD: preregistration and replay immutability, common holdout and no leakage, independent test split and null controls, intervention configuration, budget bounds, malformed plans and lock, failure mode, backend and integration regression. Benchmark is descriptive only. If no advantage is observed, preserve negative results and focus unresolved hypotheses.
