# PL5 V3.7.14 — High-throughput exact bitmap filtering

This research integration extends the existing PL5 fixed-universe filtering backend, preserving the earlier algorithms and experimental history.

## Implemented

- `research_backend/pailie5/high_throughput_v3714.py`: bit-packed masks for the 00000–99999 domain, exact AND/OR/NOT combinations, `BasicConstraint` compilation, cached rules, explicit dependency invalidation, replace/remove, and deferred expensive predicates over survivors only.
- `research_backend/benchmark_high_throughput_v3714.py`: a reproducible benchmark against existing `apply_basic_filters`; validates exact output equality for all 100,000 positions across 20-rule configurations.
- Tests: `research_backend/tests/test_high_throughput_v3714.py` and `test_high_throughput_benchmark_v3714.py`.

## Verification (Linux, Python 3.13)

- Backend full regression second run: **837 passed** (first run: 836 passed, 1 historical V3.1 CLI timeout; isolated retest passed).
- Integration: **29 passed**, for 866 tests on final run.
- Benchmark: 400 query comparisons, 0 output differences, 8.7011x warm-cache median latency ratio vs existing NumPy rule executor.
- Bitmap logical memory: 250,000 bytes for 20 full-domain rules.

This is engineering optimization only; it does not improve the probability of winning an independent fair lottery.

## Run

From `research_backend`:

```bash
python -m pytest tests/test_high_throughput_v3714.py tests/test_high_throughput_benchmark_v3714.py -q
python benchmark_high_throughput_v3714.py --output ../docs/v3714/benchmark_local.json --repeats 20 --seed 3714
```

The full cumulative research ZIP, benchmark JSON, Windows setup guidance, and source hash manifest are distributed separately from this GitHub branch. The GitHub branch does not yet contain every earlier cumulative-version file.
