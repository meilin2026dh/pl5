# SDD ledger — plan: docs/superpowers/plans/2026-11-02-v373-plan.md

Ruling: Continue the already-approved research direction without another planning question; implement in isolated extracted archive, not the user's GitHub or Windows worktree.
Ruling: Compare six equal-evaluation policies, not V3.7 versus V3.7.2 unequal budgets. This identifies contribution only in the new scheduler and specified synthetic tasks.
Pre-flight: scheduler uses existing CellDataset/FrozenOperator; runner uses the unchanged save/load/evaluate/certify API; statistical aggregation receives trial records only after all policies finish.
Baseline: extracted 775 entries from provided V3.7.2 ZIP; saved per-file source hashes; fresh full backend test running.
Review finding before implementation: V3.7.2 score uses nodes as a secondary key even at penalty=0, so true complexity ablation needs a new rank key.

Task 1: complete — 21 scheduler tests failed before the module existed, then all 21 passed. Fresh unchanged baseline: 602 backend tests passed in 86.53 seconds. New scheduler honors exact budgets, no early stop, warm charging, and true switch disabling. Evidence: 01_scheduler_red.log, 02_scheduler_green.log.
Ruling: complexity disabled means hash-based deterministic tie-breaking, not node count. Evaluation equivalence is not wall-time equivalence; archive normalization itself remains shared.

Task 2 implementation: complete — 15 runner/statistics tests failed before implementation, then 36 scheduler+runner tests passed in 3.50s. Code and experimental choices fixed before the benchmark. Existing V3.7.2 metadata/API remains the preserved historical base; new research release is identified by RELEASE_V373.json/driver/protocol rather than rewriting historical version tests.
Task 2 experiment: starting all 480 planned fits, with eight new structured tasks and two independent IID families, eight seeds, six policies and 2500 charged evaluations. No pilot outcomes used to select tasks or settings.

Task 2 experiment: complete — all 480 planned fits reached exactly 2500 charged evaluations; protocol SHA256 c453154719afda1d4a6ac9c661d8924b81a10f498bdd5dc4e2f06730774e1a42. No benchmark code/settings altered after outcomes. All four primary component contrasts are nonsignificant after Holm. Warm-start benefit not established; original default unchanged.
Task 3 checks: fresh full backend 643 passed in 83.93s; integration 29 passed in 5.39s. Independent scalar re-evaluation agrees for all 480 trials, 12 prespecified repeat fits identical except timing; all 775 historical files unchanged. Self-review documented, no separate reviewer agent available.

Task 3 release check: a fresh full-directory staging copy passed 107 focused tests in 10.89s. This repeats subsets of the 672 unique suite tests; not a new total. Packaging includes full evidence and a delta-only patch, preserving all historical bytes.
