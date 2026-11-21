# PL5 V3.7.12 — Cross-template transfer safety study

This research-only module extends V3.7.11; no deployed application changes.

## Research questions
1. Can a source-validated expression template aid transfer to a different unary-transformation family, without target test labels?
2. When source templates do not fit a target, does a bounded fallback refuse, rather than make unvalidated predictions? Can negative transfer be measured?
3. Is a target feature-slot comparison still persuasive after source-bank acquisition cost is explicitly charged?
4. Can four preplanned windows detect *observed* labeled distribution shift while protecting a family-wise false-alarm budget under a fixed iid-noise null?

## Mechanism
- A *fixed* human-authored `swap_unaries` proposal operator generates new candidates from source-certified specs, never from target holdout.
- Fixed target budget: 16 full-table feature slots. Arm A scans certified source specs, swapped specs, then canonical grammar. Arm B scans first 16 canonical grammar entries. Both must inspect the whole prespecified candidate subset and refuse ambiguous completions.
- A separately tested guarded policy uses 6 source-derived slots plus 10 canonical slots; counts duplicate evaluations, never double-counts success.
- Source certification uses only source train and independent source holdout; the source feature-search ledger (and the uncounted legacy solver cost) are disclosed. Total pipeline costs are NOT compute matched.
- Four fully preplanned labeled windows, 20 observations each, Bonferroni `alpha_total/4`; no repeated peeking, no refit, and no early prediction of drift.

## Controls and limitations
- Synthetic 10x10 functions; 70 train/30 holdout; independent target seeds/ground truth.
- Cases: unseen unary swap in three operator families, structurally incompatible target, unbanked canonical-early target, iid random table. Do not claim cross-binary-operation transfer.
- Negative transfer and abstentions must be reported, not hidden.
- No lottery prediction/production promotion. No Windows or GitHub remote deployment.
