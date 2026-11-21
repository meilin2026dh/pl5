# V3.7.18 — shared score kernel and reproducible GitHub research baseline

## Decision
Preserve the V3.7.17 default full-table ranking API and the opt-in target-only backtest. Eliminate duplicate scoring logic by using one internal scoring kernel for both. In target-only mode do not build a 100,000-row DataFrame; only extract the actual draw AFTER the full ranking is frozen.

We will not change rule selection, user-defined indicators, heuristic probability interpretation, historical time slicing, ticket ordering or statistics. We deliberately retain existing public functions and experimental opt-in flags. Comparison of full ranking and target-only results will use exact structural equality with multiple datasets, zero signal, manual rule selection, basic constraints and historical forward isolation.

The GitHub work will target an isolated research branch (not main), using a complete backend subset and a manifest of missing non-essential archival artifacts. Fresh checkout tests must actually be executed before asserting remote acceptance. An archive ZIP is the authoritative full historical artifact until Git source parity is demonstrated.

## Alternatives
- Duplicate functions, add more tests: lowest risk short term, long-term drift; rejected.
- Replace full rank with always-built DataFrame: simple but kills end-to-end speed; rejected.
- Shared NumPy computational state with two output adapters: chosen; single semantics, preserves fast path.

## Risks
- rule_details and metadata exact equality; float ordering and tie breaks; empty/manual rule keys; optional bitmap catalog; no future leakage; missing GitHub source and binary archives.
