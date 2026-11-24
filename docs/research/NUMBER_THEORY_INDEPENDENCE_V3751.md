# V3.7.51 — static-rule independent-contribution certificate

## Frozen question and source boundary
Compare the V3.7.49 **six residue partitions** and V3.7.50 **three prime-factor descriptors** with **all 58 existing V3.7.40 static Boolean keep masks**, reconstructed from the registered `_indicator_rules` and `_structure_rules` adapters. Do not read synthetic demo outcomes: pass an empty target array solely to the adapters. Preserve source masks and their SHA256 manifest. Time-varying candidate selectors, adaptive windows and unavailable private data are **outside this static Boolean comparison**.

## Precise mathematical meaning of independent contribution
For a candidate x let `s(x)` be the full 58-bit vector of existing keep/reject decisions. Every Boolean expression built solely from those existing rules is constant within each equivalence class `s(x)=s(y)`. A new descriptor `f` adds structural information **if and only if** there exist x,y in the domain with `s(x)=s(y)` but `f(x)≠f(y)`. The code exhaustively groups all 100000 IDs by old signatures and computes:

- number of old indistinguishable ID pairs, `sum_C choose(|C|,2)`;
- number of those pairs distinguished by `f`, `sum_C [choose(|C|,2) - sum_v choose(|C_v|,2)]`;
- number of split old classes;
- the first deterministic witness pair, rechecked independently against all original 58 masks and an independent trial-division factor oracle.

A nonzero value is an **exact certificate of Boolean expressiveness novelty relative to the frozen 58 static masks**, not an assertion of historical usefulness. Zero is an exact *negative* result for that comparison: the descriptor values are functions of the old 58-bit signature. Merely changing the feature value is not equivalent to adding a validated filtering rule.

## Fixed diagnostic reductions (not selected by optimization)
For the existing V3.7.39 100-ID recurrence set, separately record how many would be removed by residue=0 for p in (2,3,5,7,11,13), omega≥3, big-omega≥3 and squarefree=1. These categories are fixed before measurement. The amount removed is a **structural marginal against that one frozen baseline**, not an incremental contribution to all 58 simultaneously, not a superiority claim, and not a history-based filtering criterion.

## Reproduce
```sh
python docs/research/experiments/number_theory_independence_v3751.py
```
Three tests: exact full-domain 58-rule signature and first-witness recheck, an independent hand-enumerated small-domain partition oracle, and deterministic replay. Command prints one complete machine-readable `V3751_INDEPENDENCE_JSON` record, including the static-mask manifest digest and each feature's exact counterexample or negative proof. CI is separately configured for Ubuntu and Windows Python 3.12; successful GitHub Actions for the exact commit is required before cross-platform acceptance.

## Research limits
- This audit establishes **only deterministic static distinguishability** if witnesses exist. It does not establish independent error reduction, historical time-forward coverage, favorable cost, full-rule-library global optimality, or robustness to alternative definitions/thresholds.
- The static catalog is precisely the V3.7.40 58-mask snapshot. No claim that this encompasses all past-only/dynamic filtering methods.
- All candidate signatures are INTERNAL/AI_AUTHORED. No history, target window, hidden answer, external test or paid API is accessed.
- A future claim of practical filter contribution must fix a keep/exclude predicate before outcomes, compare full existing baselines and equal-K controls, and measure both cost and time-forward coverage. This work selects no production rule.
- Preserve negative outcomes. No edits to main, historical data, stored hashes or production code; Draft PR only.
