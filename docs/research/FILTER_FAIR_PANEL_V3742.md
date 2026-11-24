# PL5 V3.7.42 — fair, frozen, verifiable filter-evaluation panel

## Why study the upstream project

Reviewed public repository [616390260/daletou-predictor](https://github.com/616390260/daletou-predictor), README, actual `.github/workflows/predict.yml`, `evaluate.yml`, `deploy-frontend.yml`, and the persistence/evaluation tasks. Its README states an MIT license. No third-party source code, database, trained model, workflow or contact/notification service is copied into PL5. The reusable ideas are **separated creation/evaluation, per-method ledger, serialized evidence, deterministic comparisons, and a read-only dashboard contract**.

The upstream publishes multiple evaluation results, uses SQLite, and commits updated assets to the repository. Its scheduled workflow has multiple fallback times and serializes state writers with concurrency. **This does NOT establish a third-party signed timestamp or irreversible provenance**. Scheduled GitHub jobs may execute late; ordinary Git commits and force-pushable branches do not by themselves prove external custody. We must not inherit its unconditional write permissions, arbitrary force-recompute mode, notifications or automatic main commits.

## PL5-specific design

The unit of study is **one frozen candidate set on the complete 00000..99999 universe**. Every method must supply:

- Unique method ID and exact candidate IDs (sorted, ASCII, no duplicates).
- SHA256 of the method's source file bytes and SHA256 of its frozen parameter configuration, with explicit K.
- Evaluation issue, last available training issue (strictly earlier), SHA256 of the training-only input, and source evidence classification.
- SHA256 of the complete little-endian 100000-bit candidate membership bitmap.

The package stores the **full candidate members**, not merely a count or a heuristic score, and SHA256 of the canonical entire experiment payload. The evaluator refuses changed candidate members or wrong method fingerprints, changed evaluation issue, inconsistent sample type, non-ASCII IDs and mismatched content hashes.

The evaluator receives the reserved observation in a **separate call/job** and produces only retrospective containment plus exact K/100000 combinatorial retained ratio, with every method compared in the same budget group. It explicitly records that source identity and external time are **not independently authenticated**. A self-reported classification is not upgraded to cryptographic proof.

## Phase-1 engineering pilot

A reproducible internal demonstration freezes three existing method adapters at K=100:

- `affine_recurrence_filters_v3739`: existing exact 100-member recurrence conjunction.
- `engine.select_numbers`: existing position-statistics adapter with fixed candidate budget and frozen seed.
- A seeded uniformly sampled 100-member control, using NumPy's generator.

Only the first 41 rows of `data/synthetic_demo.csv` enter the freeze operation; the single row for issue `000042` is supplied exclusively to the later evaluation job. This fixture is openly synthetic and **cannot certify that information was publicly locked before a real-world event**. Frozen source SHA256 and complete bitmap fingerprints remain reproducible under the same code revision.

The workflow has three independent jobs:
1. Cross-platform Windows/Linux contract tests, including tampering and wrong-issue rejection.
2. `freeze-first` on Ubuntu: save full JSON candidate snapshot to a job artifact.
3. `evaluate-later` (depends on the other two): download the immutable snapshot from the prior job, verify it, then evaluate exactly one synthetic held-aside record.

No workflow posts a notification, contacts a paid API, deploys public pages, writes to `main`, modifies existing historical data, or forces a merge. Permission is read-only.

## Replay

```bash
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_filter_fair_ledger_v3742.py
```

The explicit two-stage CLI:

```bash
python -m pailie5.filter_fair_cli_v3742 freeze \
  --training-csv training-only.csv --evaluation-issue 000042 \
  --output frozen.json

python -m pailie5.filter_fair_cli_v3742 evaluate \
  --frozen frozen.json --observation-csv observation-only.csv \
  --output evaluation.json
```

The CLI refuses overwriting existing evidence files. The complete
candidate set and its digest must be preserved to verify any later
record. Compare K=100 methods with each other, and do not compare
a 100-candidate set's historical containment with a much larger
set without reporting the K difference.

## Still required before regular operational use

1. **Real historical source**: only use legitimately sourced, crosschecked records; preserve original bytes, source URI, raw hashes and collection timing. An upstream foreign-format database is not a PL5 data source.
2. **Completeness and chronology**: validate period sequence and input availability before freezing. Include a missing-data state; never substitute fabricated observations.
3. **Independent time custody**: if claiming advance commitment of a real experiment, use an externally timestamped and independently preserved digest, not a GitHub workflow's scheduled time.
4. **Versioned rule adapters**: bridge the entire existing PL5 experiment inventory via a strict `filter(history_prefix, frozen_config)->candidate_bitset` contract. A module that only optimizes or audits another filter is not automatically an independent candidate set.
5. **Longitudinal reports**: support matched-K cumulative retained-ratio, observed historical containment, false exclusion, processing time, overlap, redundant rules, and negatives. Publish read-only JSON first; add a Vue3 UI only when enough verified evidence exists.

This is a **minimum reproducible fair-comparison layer**, not a finished autonomous public service and not an independent time attestation.
