# V3.7.56 — Three-family frozen-filter historical retrospective coverage

## One bounded, falsifiable goal
Evaluate **all ten existing, frozen binary predicates** from V3.7.51/V3.7.54, their three family combinations, **all 1024 possible Boolean AND subsets**, and matched-candidate-count random controls on the only GitHub-available **byte-verified, dual-transcription crosschecked window**. No fitting or new rule construction is permitted. Exactly one source snapshot and one chronology split; no iterative threshold selection based on results.

## Evidence provenance (immutable, read-only)
- Primary: `pl5-cumulative/data/official_transcriptions_v3719/jiangsu_transcribed.csv`: 51 rows, issue 26244..26294; expected raw SHA256 `6962260131f6f78072bb4b0ec95514ff8ec764e1d3a2048a275e06a24644b00e`.
- Witness: `pl5-cumulative/data/official_transcriptions_v3719/gansu_transcribed.csv`: 20 rows, issue 26275..26294; expected raw SHA256 `ca0c2ef7ff02dedc8d467a0ae1c829683339f7831911b520694cb6af7df9da26`.
- Raw historical pages / publisher identity are **not independently authenticated**; this is a retrospective **CROSSCHECKED_TRANSCRIPT_NOT_ARCHIVED_SOURCE** record. The primary's first 31 rows have not been separately crosschecked.
- Fail closed on raw byte digest change, non-consecutive issue IDs, a changed crosschecked evaluation span, or disagreement between the two transcriptions. Never edit either source or their stored hashes.

## Strict chronology and fixed decisions
- Warmup rows: 31, issues 26244..26274. Evaluation: **20 paired crosschecked rows** 26275..26294.
- All ten Boolean membership arrays and all 1024 conjunction bitmaps are compiled **without reading any target outcomes**, and their full candidate membership SHA256 and exact K are recorded.
- For each issue, hash only the earlier prefix; use that and the issue ID and arm name as a deterministic seed to construct an independent, equal-K random candidate set. Commit each control's membership SHA256 before loading the issue's target value. Compare its containment in the same 20 windows.
- Per-window arm log preserves issue, prefix length, prefix digest, K, full candidate mask digest, retained / removed outcome, equal-K control digest and outcome. All 1024 coalitions retain an aggregate count and mask digest. A complete JSON is uploaded from **each** GitHub Actions platform run; machine-readable summary and full evidence SHA256 print in logs.
- Ten singleton arms, seven nonempty three-family AND coalitions, plus the empty coalition are all included (17 named arms; 1024 subset totals).
- Do not discard zero-K coalitions; report their 20 automatic removals as an explicit **empty-intersection invalidity**, not as a successful compression.
- The named-control expected retained-count reference is exactly `20*K/100000`. Do not infer a performance advantage from a small-sample difference or after searching 1024 combinations.
- No threshold optimization or calibration occurs on evaluation rows. The fixed static rules happen not to depend on the warmup, so the historical evidence tests their frozen membership rather than a trained forecasting model.

## Reproduce
```sh
python docs/research/experiments/historical_operator_walkforward_v3756.py --output ci-results/v3756-local.json
```
Five unittest cases validate source dates and crosschecking, tamper refusal, direct Boolean-mask oracle, prefix-only control seeding, and per-window conservation. For exact-source acceptance require Ubuntu and Windows Python 3.12 workflow success and inspect equal full JSON SHA256. Check separate Application checks and whole-project regression; targeted passing alone is not whole-project acceptance.

## Research limits and decision rule
This answers **retrospective fixed-filter coverage and historical removal rates** on the **20 crosschecked transcript rows** only. It does NOT establish independently archived provenance, an external pre-commitment, or representative long-range performance. These ten rules were developed during earlier research; the same historical records may have been seen during other project development, so this retrospective window must **not** be promoted to a truly unseen independent holdout.

No matched-K arm is promoted merely for looking better in these 20 rows. Searching 1024 coalitions creates severe selection risk; no post-hoc best family is a confirmed breakthrough. To establish independent benefit requires fresh, genuinely unexposed windows and locked choices, with multiple-testing controls and the same compute budget. No new methods, paid calls, historic file edits, main changes or merge.

## Actual 20-window retrospective results — verified exact source SHA

Windows and Ubuntu Python 3.12 both passed **5/5** targeted tests at commit `4c6cbecd28a1e00aa5228ae0bca84dc5873f5a9a`: [GitHub Actions #45323535358](https://github.com/meilin2026dh/pl5/actions/runs/45323535358). Both complete JSON evidence files have byte-identical SHA256 `6df9120cdd978accf2a40c7d87e700da870d241e1d61a10b99c76e674839f1f2`.

The table reports **20 target rows**; `covered` means the frozen keep set contains the historical target, `removed` is its complement. Random is **one** independently seeded matched-K control per named arm, and must not be interpreted as a statistical confidence interval.

| Frozen arm | K retained out of 100000 | History covered / 20 | History removed / 20 | Matched-K random covered / 20 | Exact reference expected / 20 |
|---|---:|---:|---:|---:|---:|
| mod2=0 | 50000 | 11 | 9 | 13 | 10 |
| mod3=0 | 33334 | 10 | 10 | 3 | 6.6668 |
| mod5=0 | 20000 | 5 | 15 | 3 | 4 |
| mod7=0 | 14286 | 1 | 19 | 3 | 2.8572 |
| mod11=0 | 9091 | 1 | 19 | 3 | 1.8182 |
| mod13=0 | 7693 | 2 | 18 | 2 | 1.5386 |
| distinct prime factors≥3 | 56540 | 15 | 5 | 12 | 11.308 |
| total prime factors≥3 | 67028 | 16 | 4 | 14 | 13.4056 |
| squarefree=1 | 60794 | 12 | 8 | 15 | 12.1588 |
| spectral C1>C2 | 49330 | 8 | 12 | 8 | 9.866 |
| modular family AND | 4 | 0 | 20 | 0 | 0.0008 |
| prime-factor family AND | 27888 | 8 | 12 | 9 | 5.5776 |
| spectral family | 49330 | 8 | 12 | 5 | 9.866 |
| modular AND prime-factor | 1 | 0 | 20 | 0 | 0.0002 |
| modular AND spectral | 0 | 0 | 20 | 0 | 0 |
| prime-factor AND spectral | 13715 | 4 | 16 | 6 | 2.743 |
| all three family AND | 0 | 0 | 20 | 0 | 0 |

**Primary engineering conclusion:** Directly intersecting all modular constraints yields only **4** candidates and removes **all 20** crosschecked historical targets. Several multi-family intersections are **empty**, which is invalid for nonempty candidate compression. This is an explicit negative result for indiscriminate AND stacking. Even if a named arm has a numerically higher historical count than a random control, the 20-row retrospective sample and previous algorithm development do **not** justify a superiority claim. The full JSON also preserves results for every one of the 1024 subsets; no after-the-fact best subset is promoted.

No existing source files or hashes changed. Technical acceptance pertains to this focused static-historical audit only; whole-project regression and external independent-source attestation are separate checks.
