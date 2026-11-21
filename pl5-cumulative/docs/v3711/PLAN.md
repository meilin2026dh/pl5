# PL5 V3.7.11 implementation plan

**Spec:** `docs/v3711/SPEC.md`

**Goal:** auditably transfer pre-certified mathematical primitive specifications between *independent synthetic tasks*, diagnose a single corrupted training label, and detect observed post-training structure drift.

**Architecture:** a separate research-only Python module uses V3.7.10 frozen primitives and additive constraint solver. A fixed candidate-feature budget applies to learned-prior and baseline arms; all source/target role separation is explicit. No real lottery inference or autonomous daemon.

**Tech:** Python 3.12+, numpy, pytest; no arbitrary code execution.

## Tasks

- [x] Inspect V3.7.10 baseline, APIs and prior experiment results.
- [ ] Test-first: independent certified source bank and target leakage prevention.
- [ ] Test-first: equal feature-evaluation budget transfer-vs-uninformed candidate order.
- [ ] Test-first: training-only single-label anomaly diagnosis with abstention.
- [ ] Test-first: fixed-window drift detection after labels arrive, with false-alarm control.
- [ ] Run frozen synthetic protocol and independent repetition, keep null results.
- [ ] Run full Python backend and bridge tests, verify packaging and prior-file preservation.

## Out of scope

LLM-driven open-ended mathematics, Windows/React live deployment, GitHub push, claims about actual lottery predictability.
