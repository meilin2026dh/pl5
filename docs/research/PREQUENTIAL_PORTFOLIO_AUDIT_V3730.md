# PL5 prequential arm-selection audit — V3.7.30 (internal method test)

## Why this exists

Historical fitting of many filtering masks can manufacture appealing backtests
even under independent fair draws. A model chosen **after** seeing each period's
winning number is not a valid historical forecasting rule. This package adds a
small, inspectable *meta-selector* for comparing already-produced fixed-budget
candidate sets under a past-only, feedback-delayed policy.

Source: `pailie5/prequential_portfolio_audit_v3730.py`.
Tests: `tests/test_prequential_portfolio_audit_v3730.py`.

## Fixed rule

Given a complete V3.7.19 `run_walk_forward` report, preserve the protocol
method order as immutable tie priority. For issue i, inspect **only** previous
settled issues with index strictly below i - outcome_delay, at most `lookback`
of those issues. Choose the arm with most prior hits. Score the selected arm's
precomputed frozen top-K candidates **only after** selection. The first
`calibration_periods` comparison periods are never scored. Include random as
mandatory reference. Missing arms, duplicate rows, mismatched target/history,
invalid fixed budgets and interleaved periods are rejected.

This estimates a prequential strategy **only if** both the base-arm algorithms
and the meta-selection rule were frozen before the target evaluation period.
Otherwise it is a descriptive, developer-internal stress check. It is not a
derivative method that selects or combines individual winning numbers: the
candidate set comes unchanged from one of the existing arms, keeping K fixed.

## Use

From `pl5-cumulative/research_backend`:

```bash
python -m pytest -q tests/test_prequential_portfolio_audit_v3730.py
python -m pytest -q tests/test_research_validation_v3719.py
```

Python usage after generating a V3.7.19 report:

```python
from pailie5.prequential_portfolio_audit_v3730 import evaluate_prequential_portfolio

audit = evaluate_prequential_portfolio(
    historical_report, calibration_periods=3, lookback=5, outcome_delay=1
)
```

The `historical_report` value must be the full return from
`run_walk_forward`, including per-period candidate SHA256 and observed
hit flags. No private source files or signing keys are required.

## Exact conditional-null checks (descriptive, NOT a significance claim)

The updated output records two **unadjusted one-sided exact tests**:

- Binomial tail for selected-arm hits among scored issues, with fixed
  `p=K/100000`. Under the iid uniform five-digit null, selection from
  past-only feedback cannot change this conditional hit probability if
  every arm's target-time candidate set is genuinely frozen and size K.
- Paired exact discordance/McNemar upper tail comparing selected arm and
  the mandatory fixed-K random control on *the same issue*. Counts include
  selected-only, random-only, both-hit and neither-hit periods; zero
  discordances yield p=1. With equal fixed sizes, uniform target draws
  imply conditional symmetry of selected-only versus control-only
  events, even when candidate sets overlap. Post-hoc tuning invalidates
  the nominal tail calibration.

Neither check adjusts for trying many windows, versions, or algorithms.
Output deliberately sets `formal_significance_claim=false` and
`predictive_advantage=NOT_ESTABLISHED` regardless of p-values.
These checks cannot verify physical pre-draw commitment or source
authenticity. A complete, well-timestamped independent prospective
protocol is still mandatory.

## Scientific limits

- **Evidence**: INTERNAL / developer-authored synthetic tests only in this work
  package. No new historical PL5 experiment is claimed, and no additional
  genuine independent blind draw is presented.
- **Causal chronology**: this algorithm excludes same-issue and future labels,
  but cannot independently prove that source candidate sets or the historical
  file existed before draw publication. Source hashes are bookkeeping, not
  an external timestamp.
- **Researcher degrees of freedom**: trying several calibration/lookback/delay
  combinations on the same evaluation period and reporting the best is
  invalid. Lock parameters before using an untouched forward evaluation.
- **Compute**: all arms must produce predictions. Total compute has not been
  equalized against a single arm; this module must not claim economic,
  operational, or predictive superiority.
- **Outcome uncertainty**: fixed K=100 corresponds to fair iid hit probability
  100/100000 = 0.001 per draw, and 10 distinct future draws provide chance
  1 - (1 - 0.001)^10 ≈ 0.009955 under that baseline. Historical hit counts alone
  cannot establish non-random advantage.
- **No actual wagering** and no assertion that filtering reveals a predictive
  signal. Keep PR in draft pending full cross-platform CI.

## Next falsifiable step (not performed here)

Pre-register one selector configuration, freeze its base-arm code and source
inventory, authenticate historical official-source snapshots without editing
original hashes, and run a genuinely untouched forward window with explicit
missing draws and multiple-testing controls. Fail to improve over the
fixed-budget random comparator => record negative result rather than inventing
another unvalidated operator.
