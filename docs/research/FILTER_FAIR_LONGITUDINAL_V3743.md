# PL5 V3.7.43 — six existing filter methods, 24-window equal-budget ledger

## Problem being tested

The previous V3.7.42 package verified *one* frozen K=100 candidate-set
experiment and a separated evaluation stage. That is not enough to
compare algorithm behavior over time. This package creates a **rolling,
source-bound, chained ledger** of the original PL5 filtering-method
adapters on the same 24 synthetic evaluation windows, freezing all
candidate sets with strictly earlier data before evaluating the reserved
row.

**This is internal synthetic development evidence only.** The fixture
`data/synthetic_demo.csv` is not a remotely authenticated original
historical source, and no independently timestamped future experiment
is asserted.

## Six predeclared candidates and matched constraint

Every method produces precisely **100 distinct five-digit IDs** for
every evaluation issue. The fixed inventory is:

1. `legacy_positional_k100` — existing positional statistics engine.
2. `legacy_pairwise_k100` — existing pairwise statistics engine.
3. `legacy_ensemble_k100` — existing ensemble engine.
4. `legacy_rank_k100` — existing full-domain heuristic ranking,
   with a frozen three-indicator pattern configuration.
5. `modular_recurrence_k100` — existing V3.7.39 exact recurrence mask,
   independent of history.
6. `uniform_control_k100` — frozen seeded uniform set, identical K.

The registry pins each method's **existing implementation source-file
SHA256**, parameters and seed plan; also records the exact 100,000-bit
membership fingerprint and the complete candidate identities. No method
receives the current observation as input.

## Complete experiment lifecycle

The dataset's last 24 rows form the **fixed** evaluation schedule,
with a 976-row starting prefix. For each issue j:

1. Build candidates using the exact earlier prefix `records[:j]`.
2. Freeze all six full candidate sets through the V3.7.42 panel
   serializer, including SHA256 over complete canonical JSON.
3. Only after the freeze object exists, evaluate the single matching
   synthetic record with `evaluate_panel`.
4. Preserve the entire frozen/evaluated pair and its SHA256.
5. Chain each pair to the previous pair's digest, so deleting,
   modifying or permuting ledger rows is detected without an
   independent recomputed root.

A verifier independently rechecks candidate membership for **every
method in every window** from the frozen full candidate-ID lists,
rejects bad chronology, wrong K, wrong issue, changed mask fingerprints,
tampered aggregated counts or mismatched chain digests. It rejects
missing/reordered windows. The chain protects against incidental
tampering, not a privileged rewrite of all evidence and hashes.

Every method gets a cumulative synthetic containment count, synthetic
false-exclusion count, and exact fixed K. No statistical advantage or
genuine historical validation is implied.

## Independently falsifiable acceptance

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_filter_fair_longitudinal_v3743.py tests/test_filter_fair_ledger_v3742.py
python -m pailie5.filter_fair_longitudinal_v3743 \
  --output ../../ci-results/v3743-local.json
```

The Windows/Linux Python 3.12 GitHub Actions workflow
`.github/workflows/pl5-filter-longitudinal-v3743.yml` executes the
same tests and the full frozen 24-window experiment. It uploads the
full JSON evidence, including complete membership lists and all
intermediate SHA256 values. The CLI refuses to overwrite a prior
experiment.

## What is still missing

- This six-arm pilot is **not the entire source code inventory**.
  V3.7.40 already enumerates earlier modules and measures 70 compatible
  configurations. Further adapters should be introduced without
  replacing methods that already work.
- The synthetic demo has no independently authenticated origin.
  Do not claim historical performance conclusions from these counts.
- The software chain and GitHub artifacts are not trusted third-party
  timestamps or independent archival custody.
- Equal candidate count does not imply equal compute cost. Future
  multi-window panels should record elapsed time, memory and exact
  operator budget under the same execution environment.
- A public read-only performance dashboard should only consume verified
  artifacts; it must never mutate frozen experiments or reclassify
  synthetic observations as independently sourced history.
