# V3.7.47 — cross-platform fixed-mask runtime evidence (2026-11-24)

## Frozen scope and provenance

One work package: inspect and preserve the measured execution-cost comparison from the already-frozen V3.7.47 tests, rather than add filtering rules. Source head `fa697d82a3e866c52c453e79cfc14811221d6c01`; tested PR merge ref `5dd34cbf1df0e409c2718d385f5664e75202d96d`. Targeted CI [45282101621](https://github.com/meilin2026dh/pl5/actions/runs/45282101621), full Python regression [45282101422](https://github.com/meilin2026dh/pl5/actions/runs/45282101422). All four emitted JSON panels were parsed from job logs; 14 execution paths × 5 measured repetitions × 2 fixtures × 2 platforms = 280 measured samples. Each panel retains the same 100 identities (99.9% candidate compression), SHA256 `45fb4e6c4443a078465f1f1ffe2ac11d3e78e88ba76000268c785784840beb7a`. Fixture classification INTERNAL/AI_AUTHORED; the twelve-rule case adds nine redundant supersets. No historical input or historical coverage measurement.

## Results (milliseconds; within-host comparisons only)

| Platform | Rules | Mode | Executor | Planner | Median total | Median planning | Five total samples (recorded order) |
|---|---:|---|---|---|---:|---:|---|
| Ubuntu | 3 | cold | scalar | input | 9.412 | 0.001 | 9.471, 9.412, 9.447, 9.370, 9.237 |
| Ubuntu | 3 | cold | scalar | greedy | 9.381 | 0.040 | 9.514, 9.362, 9.581, 9.332, 9.381 |
| Ubuntu | 3 | cold | scalar | exact | 9.583 | 0.213 | 9.635, 9.691, 9.516, 9.535, 9.583 |
| Ubuntu | 3 | cold | bitmap | count | 1.261 | 0.010 | 1.291, 1.252, 1.261, 1.396, 1.240 |
| Ubuntu | 3 | cold | bitmap | greedy | 1.216 | 0.039 | 1.216, 1.197, 1.209, 1.536, 1.287 |
| Ubuntu | 3 | cold | bitmap | exact | 1.406 | 0.199 | 1.379, 1.431, 1.335, 1.822, 1.406 |
| Ubuntu | 3 | warm | scalar | input | 8.239 | 0.001 | 8.139, 8.297, 8.090, 8.239, 8.241 |
| Ubuntu | 3 | warm | scalar | greedy | 8.196 | 0.037 | 8.218, 8.055, 8.196, 8.273, 8.186 |
| Ubuntu | 3 | warm | scalar | exact | 8.298 | 0.188 | 8.298, 8.303, 8.115, 8.446, 8.178 |
| Ubuntu | 3 | warm | bitmap | count | 0.104 | 0.007 | 0.104, 0.079, 0.091, 0.109, 0.107 |
| Ubuntu | 3 | warm | bitmap | greedy | 0.096 | 0.035 | 0.107, 0.094, 0.092, 0.096, 0.115 |
| Ubuntu | 3 | warm | bitmap | exact | 0.228 | 0.167 | 0.228, 0.222, 0.218, 0.246, 0.232 |
| Ubuntu | 3 | warm | scalar | cached_exact | 8.174 | 0.000 | 8.030, 8.242, 8.275, 8.174, 8.058 |
| Ubuntu | 3 | warm | bitmap | cached_exact | 0.067 | 0.000 | 0.067, 0.067, 0.078, 0.063, 0.064 |
| Ubuntu | 12 | cold | scalar | input | 9.924 | 0.001 | 9.943, 9.843, 11.066, 9.848, 9.924 |
| Ubuntu | 12 | cold | scalar | greedy | 10.132 | 0.355 | 10.132, 10.020, 10.444, 9.988, 10.284 |
| Ubuntu | 12 | cold | scalar | exact | 65.442 | 55.731 | 65.442, 65.710, 65.157, 65.358, 66.083 |
| Ubuntu | 12 | cold | bitmap | count | 1.578 | 0.026 | 1.584, 1.585, 1.578, 1.495, 1.565 |
| Ubuntu | 12 | cold | bitmap | greedy | 1.708 | 0.359 | 1.692, 1.728, 1.708, 1.692, 1.895 |
| Ubuntu | 12 | cold | bitmap | exact | 57.154 | 55.730 | 56.567, 56.945, 57.481, 58.474, 57.154 |
| Ubuntu | 12 | warm | scalar | input | 8.545 | 0.001 | 8.516, 8.572, 8.469, 8.620, 8.545 |
| Ubuntu | 12 | warm | scalar | greedy | 8.659 | 0.349 | 8.659, 9.464, 8.681, 8.656, 8.592 |
| Ubuntu | 12 | warm | scalar | exact | 64.398 | 55.749 | 64.272, 64.398, 63.605, 64.403, 64.581 |
| Ubuntu | 12 | warm | bitmap | count | 0.197 | 0.033 | 0.203, 0.202, 0.194, 0.197, 0.191 |
| Ubuntu | 12 | warm | bitmap | greedy | 0.443 | 0.359 | 0.468, 0.433, 0.450, 0.443, 0.421 |
| Ubuntu | 12 | warm | bitmap | exact | 56.093 | 55.916 | 77.017, 55.725, 56.425, 56.093, 55.540 |
| Ubuntu | 12 | warm | scalar | cached_exact | 8.507 | 0.000 | 8.497, 8.588, 8.759, 8.507, 8.352 |
| Ubuntu | 12 | warm | bitmap | cached_exact | 0.103 | 0.000 | 0.103, 0.107, 0.151, 0.103, 0.097 |
| Windows | 3 | cold | scalar | input | 12.000 | 0.001 | 12.270, 12.003, 11.968, 11.895, 12.000 |
| Windows | 3 | cold | scalar | greedy | 12.333 | 0.053 | 12.333, 13.060, 12.101, 13.634, 12.082 |
| Windows | 3 | cold | scalar | exact | 12.289 | 0.232 | 12.443, 12.414, 12.289, 12.238, 12.279 |
| Windows | 3 | cold | bitmap | count | 1.462 | 0.017 | 1.408, 1.460, 1.476, 1.466, 1.462 |
| Windows | 3 | cold | bitmap | greedy | 1.482 | 0.052 | 1.463, 1.500, 1.482, 1.481, 1.509 |
| Windows | 3 | cold | bitmap | exact | 1.655 | 0.227 | 1.635, 1.680, 1.662, 1.611, 1.655 |
| Windows | 3 | warm | scalar | input | 10.779 | 0.001 | 11.110, 10.820, 10.779, 10.757, 10.713 |
| Windows | 3 | warm | scalar | greedy | 10.850 | 0.052 | 14.539, 10.469, 10.885, 10.850, 10.759 |
| Windows | 3 | warm | scalar | exact | 10.984 | 0.234 | 10.984, 10.846, 11.006, 10.879, 11.011 |
| Windows | 3 | warm | bitmap | count | 0.149 | 0.017 | 0.154, 0.152, 0.149, 0.149, 0.148 |
| Windows | 3 | warm | bitmap | greedy | 0.173 | 0.052 | 0.227, 0.173, 0.172, 0.179, 0.170 |
| Windows | 3 | warm | bitmap | exact | 0.354 | 0.222 | 0.401, 0.343, 0.391, 0.343, 0.354 |
| Windows | 3 | warm | scalar | cached_exact | 10.743 | 0.000 | 10.829, 10.943, 10.691, 10.566, 10.743 |
| Windows | 3 | warm | bitmap | cached_exact | 0.137 | 0.000 | 0.137, 0.138, 0.128, 0.138, 0.130 |
| Windows | 12 | cold | scalar | input | 12.660 | 0.001 | 12.625, 20.282, 12.660, 12.646, 12.868 |
| Windows | 12 | cold | scalar | greedy | 13.103 | 0.539 | 12.863, 13.215, 12.954, 13.103, 16.746 |
| Windows | 12 | cold | scalar | exact | 84.762 | 72.238 | 84.581, 84.762, 85.120, 85.151, 81.492 |
| Windows | 12 | cold | bitmap | count | 1.935 | 0.062 | 2.018, 1.957, 1.883, 1.677, 1.935 |
| Windows | 12 | cold | bitmap | greedy | 2.149 | 0.532 | 2.149, 2.126, 2.170, 2.107, 2.456 |
| Windows | 12 | cold | bitmap | exact | 73.779 | 72.086 | 73.305, 73.783, 73.779, 73.830, 73.566 |
| Windows | 12 | warm | scalar | input | 11.063 | 0.001 | 10.857, 11.049, 11.063, 11.105, 11.101 |
| Windows | 12 | warm | scalar | greedy | 11.374 | 0.566 | 11.336, 11.305, 11.374, 11.501, 11.843 |
| Windows | 12 | warm | scalar | exact | 84.321 | 73.233 | 107.094, 84.046, 84.321, 85.331, 83.514 |
| Windows | 12 | warm | bitmap | count | 0.273 | 0.061 | 0.319, 0.242, 0.282, 0.243, 0.273 |
| Windows | 12 | warm | bitmap | greedy | 0.668 | 0.530 | 0.677, 0.664, 0.719, 0.667, 0.668 |
| Windows | 12 | warm | bitmap | exact | 73.389 | 73.111 | 73.109, 73.389, 72.760, 73.595, 73.949 |
| Windows | 12 | warm | scalar | cached_exact | 11.163 | 0.001 | 11.137, 11.418, 11.163, 11.220, 11.115 |
| Windows | 12 | warm | bitmap | cached_exact | 0.223 | 0.000 | 0.185, 0.224, 0.227, 0.213, 0.223 |

## Bounded findings and decision

- At 12 rules, scalar input, greedy and exact orders all use 111900 probes. Exact planning has no observed probe advantage; cold scalar exact is 65.442/84.762 ms versus input 9.924/12.660 ms (Ubuntu/Windows).
- Native bitmap cold cardinality-sort is 1.578/1.935 ms versus native bitmap cold exact 57.154/73.779 ms. This current exact-audit API is about 36.2/38.1 times slower on the redundant fixture. The exact audit includes two solves, hashing and reporting; not a lower bound for a specialized planner.
- Warm bitmap cardinality-sort is 0.197/0.273 ms; cached exact is 0.103/0.223 ms, excluding original plan generation and cache population. Do not interpret that as a demonstrated amortized advantage. The logical mask payloads are 37500 and 150000 bytes for 3 and 12 rules, not peak process memory.
- At three rules, greedy and exact also leave scalar probe counts unchanged (111000). Cold exact is slower than cardinality-sort for native bitmap execution on both hosts. Keep the negative comparisons; no production routing change is justified from these two fixtures alone.
- Next bounded hypothesis: independently prove redundant-mask elimination preserves the intersection, then compare against direct bitmap AND with no sorting and explicit cache build/invalidation costs. Use nonredundant controls too; do not presume an advantage.

## Technical gates and failure lineage

Targeted CI: [Ubuntu job 138068923329](https://github.com/meilin2026dh/pl5/actions/runs/45282101621/job/138068923329) and [Windows job 138068923665](https://github.com/meilin2026dh/pl5/actions/runs/45282101621/job/138068923665) each passed 16 order tests and 2 runtime tests. Full clean-machine Python: Ubuntu 1320 passed, 1 skipped; Windows 1321 passed; each 33 integration tests passed. Three other associated workflows (longitudinal ledger, exact conflict certificates, method census) succeeded. **Overall acceptance remains open:** [application run 45282101611](https://github.com/meilin2026dh/pl5/actions/runs/45282101611) failed at the previously observed 10-second `tests/innovation.test.ts:109` timeout (297 passed, 1 failed; build skipped). No timeout relaxation, no suppressed failure, no repeated CI invocation in this work package. Prior failure lineage is documented in `CROSS_PLATFORM_ACCEPTANCE_EVIDENCE_20261124.md`.

Main remains `c0e38040ec5f389d6444e64b90e7adc42adfca62`; earlier draft research heads `b5687f5e848d1fab567fcd15d8b1eb51d9e3b651` and `9c31b19ed86e754267f834d1457f1caf034b0d26` checked; PRs #11, #13, #15, #16 remain drafts, Issue #12 open. This evidence note changes no source, historical data or existing hashes. No merge.

## Reproduction

```sh
cd pl5-cumulative/research_backend
python -m pytest -q tests/test_weighted_filter_order_v3746.py
python -m pytest -q -s tests/test_filter_runtime_v3747.py
```

Original nanosecond samples, acquisition, planning, execution and materialization, order, mask fingerprints and software metadata are in the linked CI job logs. Rounded milliseconds in this note are descriptive, not acceptance thresholds. Single runner per platform, five repetitions, intentionally redundant stress fixture; no inference of general runtime superiority or historical exclusion rate.
