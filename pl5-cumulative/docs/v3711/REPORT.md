# PL5 V3.7.11 — cross-task transfer, noisy training diagnosis, labeled drift monitoring

## Executive research summary

The researcher did **not** discover a new universal mathematical axiom. It reused three mathematical primitive *structural templates* from independently tested synthetic source tasks (one `xor_shift`, one `abs_scaled`, one `gcd_shift`), learned each target's coefficients/latent arrays from target training data only, and compared the candidate-prioritized search against the same fixed-size candidate-feature budget in V3.7.10's canonical grammar order.

### Primary frozen study: 6 target seeds × 6 task cases = 36 trials

| Case | Trials | Observed outcome |
|---|---:|---|
| Independent target tasks in three same-family structured classes | 18 | 18/18 transfer fits; 18/18 target holdout scores exact (540/540 test digits); baseline 0/18 accepted at 8 candidates |
| Independent uniform-random operation tables | 6 | 6/6 transfer abstained |
| Artificial single-label corruption in target training | 6 | 6/6 location and correction hypothesis identified; fitting on corrupted data abstained |
| Controlled regime shift between training and new label measurements | 6 | 6/6 signaled after a fixed window of 20 new labels; frozen model missed 162/180 shifted holdout labels |

In positive trials, **all target model fits were frozen before scoring the 30 held labels**. The three source tasks themselves passed a separate source-only held-out certification. Model specification selection was never based on target heldout responses.

All target trials checked **8 full-table mathematical feature specifications** in each arm; the upstream discovery and source validation cost is **excluded**. Therefore this is not a fair total-runtime, total-energy or end-to-end evaluation comparison. The baseline is a fixed naive grammar enumeration, not the strongest known adaptive optimizer.

### Supplemental, separate stress protocol: 66 new trials

- 18 additional near-family target tasks: all 18 accepted with zero held errors.
- 24 independently seeded iid random operation tables: all 24 abstained.
- 12 additional single-label corrupted target tasks: all 12 uniquely located the edited cell and reconstructed the expected digit in the stated synthetic setup.
- 12 further shifted-rule observations: all 12 flagged after 20 new labels.

This stress study was run after developing the methods, is distinct from the frozen primary protocol, and is not a genuinely unseen *real-world* independent replication.

### Statistical safeguards and missing guarantees

- The positive cases share exactly the model family types used by the source tasks; the experiment demonstrates **within-family primitive reuse**, not discovery of arbitrary new structures.
- Candidate budget equality does not imply matching all computation costs. No valid claim of end-to-end speed advantage is justified.
- The noise model assumes **a single** digit-label corruption. Identifying a unique hypothetical correction does not prove the observation was erroneous; no database entry is auto-edited.
- Drift monitoring waits for 20 new labeled examples and computes an exact binomial upper tail under an explicitly assumed iid 2% error-rate null with a fixed α=0.001. The statistical calibration is conditional on this hypothetical null, correct chronology and one prespecified look; repeated monitoring or dependent observations require adjusted control.
- The system cannot tell whether a future drift will occur before receiving new observations; the 162/180 shifted errors are a failure case, not a model success.
- No actual lottery data is used, and no excess lottery predictive or filtering power is established.

### Reproducibility

The CLI `cd research_backend && python research_transfer_v3711.py --output ../runs/v3711` writes deterministic frozen `protocol.json` and `results.json`. The baseline version archive has been preserved. See SHA256 and verification output in adjacent files.

### Engineering/production boundary

This release is **research preview**. Python backend and integration regression results are saved independently; Windows and React production validation, GitHub synchronization, deployment to `D:\pl5`, new control-system integration, and genuine real-time source validation are **not** claimed.

### Next scientific problem

Test transfer to **family-disjoint unseen operator structures** with identical *total compute* budgets, calibrated abstention, naturally occurring noise, multiple-testing correction, and sequential drift detection with time-ordered provenance.
