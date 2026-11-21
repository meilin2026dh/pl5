# Execution ledger — docs/superpowers/plans/2026-11-02-v372-plan.md
Baseline: uploaded archives copied into a new isolated sandbox directory; original archives unchanged.
Ruling: user repeatedly approved direct continuation; no new approval loop for existing research scope.
Ruling: reuse V3.0 AST rather than introduce duplicate semantics; search output alphabet grows to10.
Pre-flight: AST outputs integer vectors -> search applies final mod10; frozen artifact -> evidence uses same expression and independent scalar verification.
Baseline failure: V3.7.1 imports math_language_v37 as a top-level module instead of a package sibling.

Task 1 complete: package imports fixed. Previous five tests, V3.7/V3.5/V3.6 tests and new package regression executed; see evidence/02_import_after.txt.

Task 2: AST uses V3.0 integer evaluator, bounded JSON decoder, semantics-preserving simplification and seeded structural mutation/crossover. Tests: evidence/06_ast_after.txt.

Task 3: training-only search, immutable operator, no-refit evaluation, independent scalar certification, integrity-checked exports implemented. New tests: evidence/10_new_tests.txt.
Historical baseline: full backend suite 540 passed in 79.60s (evidence/04_baseline_full.txt).

Adversarial fix: a one-evaluation budget plus an overflowing warm start left no valid champion. Reproduced in evidence/11_edge_before.txt; reserve one charged safe baseline evaluation. Also test integer-behavior deduplication rather than unsafe modulo-output deduplication.

Task 4 complete: 18 benchmark trials plus deterministic replay; final backend 602 passed, integration 29 passed. No network, shared-branch push, main merge or Windows host changes.
Ruling: keep isolated branch as a delivery workspace; user asked to continue research, not to merge remotely.
