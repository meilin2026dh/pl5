# PL5 V3.7.12 — bounded transfer, negative transfer, and multiple-look drift controls

This independent **research preview** extends all files of `PL5_V3711_Full.zip` without altering prior sources, datasets, or historical experiment logs.

## New files
- `research_backend/pailie5/template_transfer_v3712.py`: source-certified candidate priority (original, swapped unary, shifted-left unary), frozen full-table fit, target budget parity, source acquisition ledger.
- `research_backend/pailie5/shift_windows_v3712.py`: four fixed post-label windows, Bonferroni family-wise alpha, no refitting.
- `research_backend/pailie5/template_study_v3712.py`: reproducible 36-target trial, negative-transfer, random-table, and 512-schedule iid-null simulation.
- `research_backend/research_transfer_v3712.py`: explicit one-shot CLI; **not** a background agent.
- `research_backend/tests/test_*_v3712.py`: regression and falsification tests.
- `docs/v3712`: registered design, protocols, actual results, replay evidence and test outputs.

## Reproduce with Python 3.12+ and existing numpy/pytest dependencies

```powershell
cd research_backend
py -3.12 research_transfer_v3712.py --output ..\runs\v3712
py -3.12 -m pytest -q tests\test_template_transfer_v3712.py tests\test_shift_windows_v3712.py tests\test_template_study_v3712.py
```

## What it actually establishes
- Fixed **target** budget: 16 full-table feature candidates each, with independent holdouts.
- Target knowledge is useful for certain related unary-template transformations, but can harm when a useful canonical candidate falls outside the remaining fixed budget.
- Source certification examined an additional 1,104 distinct source feature tables (not including legacy candidate solvers). This makes full-pipeline cost strictly *unmatched*. There is **no demonstrated full-pipeline computational advantage**.
- Monitoring requires **subsequently observed labels**, a prespecified four-look schedule, and an iid-error assumption. It cannot forecast lottery outcomes or pre-observation drift.
- `production_enabled=false`, `predictive_advantage=NOT_ESTABLISHED`.
- The live application `research_backend/pyproject.toml` still reports 3.7.6. Version 3.7.12 refers to this research package, not a deployed app version.
- Not deployed to `D:\pl5`, no GitHub sync, Windows/React/Streamlit build not validated.
