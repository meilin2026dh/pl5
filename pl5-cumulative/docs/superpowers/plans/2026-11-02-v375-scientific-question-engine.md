# V3.7.5 Scientific Question Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver auditable scientific question–hypothesis–experiment cycles integrated with PL5 V3.7.4.

**Architecture:** A new `scientific_questions_v375.py` derives a reproducible problem registry from frozen V3.7.4 results and chooses an intervention. A minimal V3.7.4 protocol extension accepts a focus only before generating a new immutable cycle; a new `research_scientific_v375.py` CLI runs bounded cycles using the existing shared lock.

**Tech Stack:** Python 3.12+, NumPy, existing PL5 package, pytest; JSON journals.

**Spec:** docs/superpowers/specs/2026-11-02-v375-scientific-question-engine-design.md

## Global Constraints
- Synthetic mathematical benchmarks only; no predictive advantage claimed.
- Never modify completed V3.7.4 cycle results or saved operators.
- Training-only candidate selection; held-out data opened after freezing all arms.
- Every experiment has an immutable plan and is capped by existing V3.7.4 budget.
- Random negative-control cadence remains enforced, irrespective of focus.
- No uncontrolled background operation, account access or autonomous source modification.

## Review Focus
- Invalid or stale question focus: reject before protocol creation.
- User's existing historical run: resume without overwriting any old evidence.
- Crash between plan and execution: replay locked plan exactly, no relabeling.
- Existing `.run.lock`: refuse rather than corrupting the workspace.
- Null-control: cannot be displaced by discretionary question prioritization.

---

### Task 1: Problem catalog and differentiating experiments
**Files:** Create `research_backend/pailie5/scientific_questions_v375.py`; tests `research_backend/tests/test_scientific_questions_v375.py`.
**Interfaces:** `build_registry(root: Path, state: dict) -> dict`; `choose_experiment(registry: dict, state: dict) -> dict`.
- [ ] Write tests for issue genealogy, three falsifiable hypotheses, prioritization, cost/novelty, investigation quota.
- [ ] Run failing tests.
- [ ] Implement observation extraction solely from completed cycle records and deterministic candidate selection.
- [ ] Run focused tests and commit.

### Task 2: Frozen scientific plan integration
**Files:** Modify `research_backend/pailie5/autonomous_v374.py`; create `research_backend/pailie5/scientific_runtime_v375.py`; extend V3.7.5 tests.
**Interfaces:** `run_scientific_cycles(output, cycles, budget, seed, control_every) -> dict`.
- [ ] Write tests proving preselected focus changes V3.7.4 protocol and cannot bypass periodic random control.
- [ ] Verify tests fail.
- [ ] Implement shared-lock execution, immutable plan, crash replay, V3.7.4 call and registry reconcile.
- [ ] Run focused tests and commit.

### Task 3: CLI, real resume and cumulative release
**Files:** Create `research_backend/research_scientific_v375.py`, `README_V375.md`, `docs/v375/REPORT.md`, reproducibility evidence, cumulative ZIP.
**Interfaces:** CLI args `--output --cycles --budget --seed --control-every`.
- [ ] Write failing CLI tests.
- [ ] Implement CLI; run against copy of the previous eight V3.7.4 cycles, then verify unchanged prior files and distinct new seeds.
- [ ] Run all `research_backend` and `integration_tests` suites, report actual test counts and failures; document limitations.
- [ ] Commit source changes and generate cumulative, hash-verified release in `/mnt/data`.
