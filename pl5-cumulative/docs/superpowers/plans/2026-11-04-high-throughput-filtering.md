# High Throughput Filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add exact cached bitmap filtering and verify performance against the existing PL5 vectorized NumPy oracle.

**Architecture:** New stand-alone `high_throughput_v3714.py` builds safe bitsets from `BasicConstraint` and explicit masks; optional expensive predicates are evaluated only for survivors. A separate benchmark reports cold and warm figures, validates every query against the legacy oracle, and stores hardware-independent result counts.

**Tech Stack:** Python 3.12+, NumPy, pytest, standard-library time/perf_counter, zipfile.

**Spec:** `docs/v3714/DESIGN.md`

## Global Constraints
- Full domain 00000 to 99999, strict exactness.
- Maintain prior cumulative code unchanged except additive files.
- Benchmark repeats, discloses runtime host and exact baseline semantics.
- Only static or explicitly invalidated predicates are cached.

## Review Focus
- Leading zeroes in ticket numbers: verify formatting.
- Stale dependent cache: explicit invalidation and update tests.
- Empty OR / empty AND / unknown rules: deterministic semantics.
- Mutable client masks: freeze at registration.
- Deferred rules used inside OR/NOT: reject clearly.

### Task 1 — Exact mask compiler
**Files:** Create `research_backend/pailie5/high_throughput_v3714.py`; tests `research_backend/tests/test_high_throughput_v3714.py`.
- [ ] Add failing tests for bit packing/unpacking and `BasicConstraint` equivalence.
- [ ] Run RED, implement minimal compiler, run GREEN.

### Task 2 — Cache lifecycle and deferred evaluation
**Files:** Same module/tests.
- [ ] Add failing tests for updates, invalidation, boolean composition, deferred survivor counts, validation.
- [ ] Run RED, implement safe engine, run GREEN.

### Task 3 — Benchmark and reports
**Files:** `research_backend/benchmark_high_throughput_v3714.py`, `docs/v3714/REPORT.md`, JSON benchmark.
- [ ] Implement reproducible baseline vs bitmap benchmarks.
- [ ] Run under same interpreter and verify exact outputs on all input queries.
- [ ] Report cold-build, warm-query, reconfiguration, memory and host details.

### Task 4 — Regression, packaging, source sync
- [ ] Run new tests, full back-end tests and bridge tests.
- [ ] Preserve all legacy files, repackage, verify ZIP CRC and re-extract + smoke tests.
- [ ] Sync additive source to isolated GitHub research branch and verify fetched content; never assume main updated.
