# PL5 V3.7.13 — test design, codebook dispersion and risk audit

Scope approved in conversation: implement three discussed methods in cumulative research source, do not replace any earlier features. Implement with Python3.12+ using existing scipy dependency for exact binomial bound.

1. `covering_arrays_v3713.py`: deterministic algebraic covering arrays of strength 2/3 for PL5 and independent exhaustive interaction audit; 100% covered with no optimality claim. Unrestricted construction only: constrained selection cannot promise coverage.
2. `codebook_v3713.py`: strict ASCII PL5 identifiers, one-hot MCWC representation (50 bits, weight 5), digit Hamming separation, deterministic cardinality-limited greedy interaction-covering selection from approved candidates; independent distance and coverage audits.
3. `conformal_audit_v3713.py`: split-conformal rank threshold with finite-sample n+1 correction; if kth index > n use full 100k domain. Frozen model hash and strict chronology required; a holdout audit reports marginal coverage, upper one-sided exact Clopper-Pearson risk bound and fair-lottery baseline. A separately frozen fixed-filter audit measures binary miss rate without falsely calling it a conformal guarantee.
4. `research_v3713.py`: CLI generate, optimize, calibrate and synthetic demo; machine-readable output with evidence provenance and clear non-predictive labeling.
5. Tests first: independent exhaustive pair/triple verification, invalid numeral Unicode, minimal distance/retention, empty/infeasible requests, quantile edge cases, freeze/chronology and no-outperformance claims. Full suite + bridge tests + packaged extraction check.

Research-only. No automatic deployment, no external provider used, no predictive advantage claims; cross-date independence and genuine pre-commitment cannot be established from caller-supplied data without external validation.
