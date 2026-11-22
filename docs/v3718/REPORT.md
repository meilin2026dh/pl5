# PL5 V3.7.18 — Shared scoring kernel and executable research source baseline

## Engineering change
The old full-table and target-only rank paths now delegate to the same `_rank_core_v3718()`, preserving 100,000 candidate evaluations, rule selection, tie breaking, historical forward slicing and `00000` formatting. This reduces duplicate research logic without claiming new forecasting power.

## Verification from this research session
- Full cumulative research workspace: **877 backend tests** + **29 integration tests**, zero failures.
- Isolated reconstruction from only **597 expected GitHub source/dependency files**: again **877 backend tests** + **29 integration tests**, zero failures. This is a content-level reconstruction, not an actual git clone.
- SHA audit: 596 paths match exact Git Blob SHAs; original PL5 research `README.md` was copied to `docs/v3718/README_CUMULATIVE_SOURCE.md` with matching SHA to preserve the root README for the existing 五序 web application. Hence 597/597 source items accounted for.
- 2 seeds (3718, 3719), 4 benchmark repeats each, comparing V3.7.17 vs V3.7.18: **all workflow output hashes match**; latency changes fluctuate in both directions, so no universal speedup claim.
- The old ZIP baseline has 2,580 files; the new cumulative ZIP has 2,587, with only `probability_ranker.py` modified among old files.

## Limits
- GitHub research branch is an *executable research code/dependency subset*, **not a full mirror of all 2,587 cumulative historical archive files**.
- Full Windows 3.12 and React production build are unverified; `main` has not changed.
- Inputs are synthetic/constructed research fixtures; there is no evidence of predictive lottery advantage.

**Source-of-truth cumulative release:** `PL5_V3718_Full.zip` and its SHA256 release audit, produced separately in this conversation.
