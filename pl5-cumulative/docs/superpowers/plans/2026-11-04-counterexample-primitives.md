# PL5 V3.7.10 Counterexample-Driven Primitive Generation Implementation Plan

> **For agentic workers:** Implement tests before production code; use deterministic bounded experiments.

**Goal:** Generate and falsify compositional interaction candidates from training-only contradiction witnesses when V3.7.9 cannot explain a synthetic 10×10 table.

**Architecture:** An additive-rectangle contradiction screen identifies residual patterns; a finite type-safe grammar *generates* composed terms from unary transformations and binary operations, solves additive residuals, and accepts a frozen operator only if all consistent completions agree. Existing V3.7.9 is the comparator; held-out labels are invisible to fitting.

**Tech stack:** Python 3.12+, NumPy, existing CellDataset, pytest; no dynamic eval or external service.

**Scope & limitations:** mathematical candidate grammar is bounded and human-designed; no invention of general mathematical laws or lottery advantage. Classify ambiguity, noise, and external drift as abstentions. User-requested continued research authorizes implementation in an isolated copy; no live deployment or GitHub mutation.

## Checklist
- [ ] Inspect V3.7.9 fitter and tests, identify true boundaries.
- [ ] Add failing tests for new composed candidates, noise, random tables, budget and train/held-out separation.
- [ ] Implement finite grammar generation, contradiction-guided parameter elimination, model freezing/abstention.
- [ ] Run new tests, then full backend and integration regression.
- [ ] Register sealed synthetic protocol with external-form, corruption and drift controls, execute and replay.
- [ ] Compare to legacy under transparent compute budget (no equal-cost superiority claims).
- [ ] Verify zip CRC, per-file preservation, release manifest and unpack smoke tests; deliver integrated ZIP and compact patch.
