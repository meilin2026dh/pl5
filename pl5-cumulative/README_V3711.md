# PL5 V3.7.11 — cross-task mathematical-primitive transfer (research preview)

This version **extends the complete V3.7.10 archive**. It does not replace the earlier modules, historical experiment records, and the V3.7.6 Hotfix 1 security fixes.

## Scientific question

Can a finite mathematical primitive learned and independently verified on one synthetic task reduce candidate search on a separately generated task, under a matched candidate-feature evaluation budget? Can the system diagnose one corrupted training label and detect **observed** rule changes?

## New files

- `research_backend/pailie5/cross_task_v3711.py` — source-certified frozen bank, budgeted transfer and baseline, single-label train-only diagnosis, observed fixed-window drift alarm.
- `research_backend/pailie5/transfer_study_v3711.py` — deterministic 36-trial preregistered synthetic protocol.
- `research_backend/research_transfer_v3711.py` — CLI to reproduce the finite study.
- `research_backend/stress_transfer_v3711.py` — separate 66-trial supplemental stress suite.
- `research_backend/tests/test_cross_task_transfer_v3711.py`, `test_transfer_study_v3711.py` — regression tests.
- `docs/v3711/` — methodology, executable plan, official and stress results, replay audit, test logs, version audit.

## Run on Windows (PowerShell)

From project root with the existing Python dependencies installed:

```powershell
cd research_backend
py -3.12 research_transfer_v3711.py --output ..\runs\v3711
py -3.12 -m pytest -q tests\test_cross_task_transfer_v3711.py tests\test_transfer_study_v3711.py
```

Do not run these commands inside a package install path without first extracting the complete archive.

## Interpretation boundaries

1. Tests and benchmarks use **synthetic 10×10 digit-operation tables**, not historical lottery draws.
2. An identified model is **provisional within only the 8 inspected candidates**, not mathematically universally identified.
3. The baseline uses the same 8 feature-evaluation slots, but the *upstream source-bank discovery cost and wall time are not matched.*
4. Structured source and target tasks share the researcher's designed structural families: this is near-family transfer, not open-world task generalization.
5. Drift is detected after 20 new labeled observations and the binomial test assumes a fixed iid 2% model-error null; actual chronological provenance is the caller's responsibility.
6. Noise diagnoses are hypotheses, never automatic label corrections.
7. This research preview has **not** been deployed to `D:\pl5`, synced to GitHub, built as a Windows app, or integrated into the long-running autonomous research scheduler.

`research_backend/pyproject.toml` retains the previous application version `3.7.6`; the independent **research package** version is `3.7.11` only. The deployed product version has not changed.
