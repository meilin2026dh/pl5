# V3.7.6 Scientific Method Design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add controlled, self-selected experimental methods that follow unresolved questions in V3.7.5 and produce auditable independent results.

**Architecture:** Isolated method-design module consumes the historical problem registry read-only, produces preregistered two-arm interventions and executes via existing frozen AST operators. CLI handles bounded execution and passes through unchanged historic state. No unsafe dynamic code.

**Tech Stack:** Python 3.12+, NumPy, existing PL5 modules, pytest, JSON.

**Spec:** `docs/superpowers/specs/2026-11-02-scientific-method-design-v376-design.md`

## Global Constraints
- Research only, production_enabled false, no gambling claims.
- Never modify V3.7.5 records; new output lives under `runs/autonomous_v376`.
- Every intervention shares a strictly held-out set of 20 input pairs and isolates model selection from those answers.
- Always fixed finite budgets; negative control every 4th study.

## Review Focus
- Existing plan tampering or resumed partial write -> refuse to proceed.
- Any overlapping train and holdout pair -> refuse.
- Same-method repeated trials/split leakage -> fresh seed and independent new trial.
- All test results near random -> mark unresolved; never enable production.
- Injected invalid cost settings or concurrent process -> refuse.

### Task 1: Method proposal and intervention specification
**Files:** Create `research_backend/pailie5/scientific_methods_v376.py`; Test `research_backend/tests/test_scientific_methods_v376.py`.
**Interfaces:** `propose_study(history_registry: dict, study_history: list, study_number: int, seed: int, budget: int, control_every: int) -> dict`.
- [ ] Write tests for three intervention classes, unique seeds, random controls, locked test size, and price ceilings.
- [ ] Observe failures for missing implementation.
- [ ] Implement deterministic method selection and preregistered study specification.
- [ ] Run targeted tests and record outputs.

### Task 2: Frozen paired experimental runner
**Files:** Create `research_backend/pailie5/scientific_runtime_v376.py`; extend tests.
**Interfaces:** `run_method_studies(output: Path, historical: Path, *, studies: int, budget: int, seed: int, control_every: int) -> dict`.
- [ ] Write tests for real two-arm execution, common heldouts, frozen operators before labels, resumability, tampering, lock and non-production results.
- [ ] Observe expected failures.
- [ ] Implement split, fit, freeze, evaluate, record and reconcile under exclusive lock.
- [ ] Run targeted tests.

### Task 3: CLI, research run, audit, and package
**Files:** Create `research_backend/research_methods_v376.py`, `README_V376.md`, `RUN_V376_ONCE.cmd`, `docs/v376/REPORT.md`, `docs/v376/VERIFICATION.json`; update version metadata in project.
- [ ] Write/test CLI, including invalid input handling.
- [ ] Run a fresh 4-study experiment based on prior 12 cycles; verify old archive files unchanged.
- [ ] Run full backend and integration suites; save logs, frozen experiments and checksums.
- [ ] Package cumulative ZIP, reopen and verify files and key tests.
