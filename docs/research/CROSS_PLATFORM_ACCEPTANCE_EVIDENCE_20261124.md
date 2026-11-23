# PL5 cross-platform filtering regression evidence — 2026-11-24

## One bounded task: close the pending CI gates at the exact tested source heads

No new filtering algorithm or source change is introduced here. This is a durable verification record, not a new execution or an assertion that a later commit was tested. GitHub Actions job conclusions and the latest V3.7.45 full-job logs were inspected directly.

| Draft PR | Tested source SHA | Full fresh-machine Ubuntu/Windows | Application |
|---|---|---|---|
| #11 | `b5687f5e848d1fab567fcd15d8b1eb51d9e3b651` | [45186730980](https://github.com/meilin2026dh/pl5/actions/runs/45186730980): both success, both acceptance gates success | [45186730762](https://github.com/meilin2026dh/pl5/actions/runs/45186730762): success |
| #13 | `9c31b19ed86e754267f834d1457f1caf034b0d26` | [45220436713](https://github.com/meilin2026dh/pl5/actions/runs/45220436713): both success, both acceptance gates success | [45220436786](https://github.com/meilin2026dh/pl5/actions/runs/45220436786): latest attempt success |
| #15 | `35b481f89573d5432decb3c727c42a71edcbfc15` | [45242431995](https://github.com/meilin2026dh/pl5/actions/runs/45242431995): both success, both acceptance gates success | [45242432080](https://github.com/meilin2026dh/pl5/actions/runs/45242432080): success |

The main branch source remains `c0e38040ec5f389d6444e64b90e7adc42adfca62` at inspection. All three PRs remain draft. Issue #12 independent evidence gates remain open.

## V3.7.45 full regression log evidence

| Test family | Ubuntu Python 3.12 | Windows Python 3.12 |
|---|---:|---:|
| Full research backend | 1310 passed, 1 skipped (192.72 s) | 1311 passed (244.38 s) |
| Full legacy integration | 33 passed (4.47 s) | 33 passed (9.52 s) |

Direct job links: [Ubuntu 137930322950](https://github.com/meilin2026dh/pl5/actions/runs/45242431995/job/137930322950), [Windows 137930323463](https://github.com/meilin2026dh/pl5/actions/runs/45242431995/job/137930323463). The skip is retained explicitly; the platform pass totals are not described as identical. The run logs also report successful dependency checks, Python source compilation, history replay/archive verification, preserved tracked-file state, artifact upload, and final acceptance gates. Elapsed times are CI observations only, not a controlled filtering performance benchmark.

Recorded commands from the full-job logs:

```sh
cd pl5-cumulative/research_backend
python -m pytest --collect-only -q tests
python -m pytest -q tests --junitxml=../../ci-results/backend.xml
cd ..
python -m pytest -q integration_tests --junitxml=../ci-results/integration.xml
```

Focused replay from the same source head:

```sh
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_filter_compatible_repairs_v3745.py tests/test_filter_conflict_certificates_v3744.py
```

[45242432102](https://github.com/meilin2026dh/pl5/actions/runs/45242432102) targeted jobs: both success. [45242431980](https://github.com/meilin2026dh/pl5/actions/runs/45242431980) source census: both success. All seven returned PR workflow runs at this exact V3.7.45 source SHA concluded successfully, including the preceding frozen filtering ledger and conflict audits.

## Failure genealogy (do not erase earlier failures)

- [45231651468](https://github.com/meilin2026dh/pl5/actions/runs/45231651468): both exact conflict test jobs failed; prior PR record identifies the obsolete source-chain digest assertion. The corrected later conflict workflow passed.
- [45242068566](https://github.com/meilin2026dh/pl5/actions/runs/45242068566): both census/test jobs failed; prior PR record identifies missing registration of the new structural audit module. The subsequent census workflow passed.
- [45220436786](https://github.com/meilin2026dh/pl5/actions/runs/45220436786): PR #13 records the earlier application timeout. The latest job conclusion is success; this does not establish elimination of timing flakiness.

## Evidence limits and next gate

Technical acceptance is supported for the three exact tested source heads, within the declared CI suites and recorded skip. This documentation-only commit is not the tested source SHA. No assertion of independent reproduction on a user machine, authenticated chronological historical coverage, or historical exclusion rate follows. Internal synthetic windows and AI-authored development cases retain their existing classifications. No historical data or recorded hashes, source modules, main, hidden files or Issue #12 were modified. No merge. Further candidate-set compression research should distinguish membership-probe cost from fixed-width bitmap intersection and upstream rule generation cost; no new algorithm is warranted without a frozen testable hypothesis.
