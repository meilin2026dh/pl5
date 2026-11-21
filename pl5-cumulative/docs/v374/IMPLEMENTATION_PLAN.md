# PL5 Autonomous Research Loop Implementation Plan

> **For agentic workers:** Use TDD, run tests first to observe failure and then pass.

**Goal:** Execute a bounded, resuming, self-selecting offline research process over existing safe math expression engines.

**Architecture:** A deterministic controller persists predeclared protocols and frozen operators per cycle; a training-only selector chooses reusable expressions; a diagnosis stage proposes subsequent experiments using new seed splits. Existing fitter and independent scalar certifier remain unchanged.

**Tech Stack:** Python 3.12+, NumPy, SciPy, pytest, existing PL5 research backend.

**Spec:** docs/v374/DESIGN.md

## Task 1 - Knowledge selector
- [ ] Write tests proving it never reads holdout values and deduplicates/validates subtree expressions.
- [ ] Observe test failure before implementation.
- [ ] Implement `select_warm_starts(train, bank, max_items)` using training only and deterministic scoring.
- [ ] Run tests and commit.

## Task 2 - Autonomous controller
- [ ] Write tests for bounded cycles, unique seed splits, immutable artifacts, recurring control, task adaptation, error diagnostics.
- [ ] Observe failure before implementation.
- [ ] Implement `run_cycles(root, cycles, budget, seed)` to save protocol, freeze all operators, and evaluate only afterward.
- [ ] Run tests and commit.

## Task 3 - CLI and local execution
- [ ] Add CLI and Windows Task Scheduler script template, without automatically registering tasks.
- [ ] Execute bounded cycles and record real outputs.
- [ ] Run full backend and integration tests; package cumulative source, scripts and results, without making unverified prediction claims.
