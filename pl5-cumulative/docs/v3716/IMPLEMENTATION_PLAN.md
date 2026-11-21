# PL5 V3.7.16 — end-to-end exact-bitset integration

**Goal:** Reuse V3.7.14 exact bitsets across existing PL5 workflows while preserving complete semantics and measuring end-to-end benefits, not isolated bitwise kernels.

**Chosen approach:** Opt-in reusable `BasicFilterCatalog` keyed by immutable `BasicConstraint`, passed into (1) basic + pattern intersection, (2) rank creation and rolling rank research, and (3) history sculpting and rolling sculpt research. Default legacy paths remain untouched. Do not cache history-dependent pattern masks or lottery predictions.

**Alternatives considered:** (a) globally monkey-patch the legacy evaluator: rejected due to cache staleness and hidden semantics; (b) force all flows through bitmap engine: rejected because one-shot cold builds could regress.

## Tests / execution checklist
- [x] TDD red tests: single and multi-rule selection, unknown rule rejection, cache invalidation, collision semantics.
- [x] Green: catalog adapter on existing V3.7.14 `ExactFilterEngine`.
- [x] TDD red then green: basic+pattern intersection, rank path and rolling rank path, sculpt path and rolling sculpt path.
- [x] Independent full-universe numerical equality and metadata equality; no results from future draws enter training.
- [x] Benchmark synthetic (not real historical draw) data using actual PL5 pattern/sculpt/rank pipelines and query batches; separate cold creation, hot repeated runs and full end-to-end.
- [x] Report negative results if end-to-end pipelines are dominated by other work.
- [x] Rerun backend complete pytest + cross-module integration tests; release cumulative ZIP & incremental patch, source SHA audit.
- [x] Publish changed source to a new GitHub research branch, state if branch still lacks cumulative historical sources.

**Safety:** Historical pattern context not cached; unchanged fair-lottery no-forecast disclaimer. Invalidation required on mutable custom indicators. Bench comparisons use the same data, same steps and shuffled order with a fixed seed, report raw runs and platform information.
