# PL5 V3.7.41 verified reference results and CRAN execution gate

## Versioned experimental result (actual execution)

| strength t | GF(11) start | 32-seed best N | seed | required interactions | missing | thin interactions (covered exactly once) |
|---|---:|---:|---:|---:|---:|---:|
| 2 | 120 | 119 | 0 | 1000 | 0 | 810 |
| 3 | 1330 | 1288 | 0 | 10000 | 0 | 7410 |
| 4 | 14361 | 12367 | 5 | 50000 | 0 | 38334 |

This is full t-way coverage, **not** full 5-way identity coverage.

All starting arrays derive from the same original PL5 V3.7.13
GF(11) polynomial generator. A fixed 32-seed multi-start
**deletion-only** optimizer removes a row only when every one of its
required interactions remains duplicated. A separate exact tuple counter
and the existing V3.7.13 interaction verifier both report zero missing
tuples for the final sets.

The output rows have stable SHA256 (five ASCII digits per line, sorted
order inherited from the initial algebraic array after deletion, LF
termination):

| t | best-array SHA256 |
|---|---|
| 2 | `14e0660e4efc8147a1acc903ea92a016f286072adc66fc88bf010409b1ec34ee` |
| 3 | `82e464f26026f486bdede8f778d9a614f1c73b19cab1a76d029af7b117775db3` |
| 4 | `d4ebe5cbaa5c44a2a3e40fd431a213a2939d1da14474f7b646e666c5366a1fc8` |

## Independently repeated cross-platform technical checks

[GitHub Actions run #45217523533](https://github.com/meilin2026dh/pl5/actions/runs/45217523533)
ran the same Python generator and its legacy plus new covering
tests under Python 3.12 on both operating systems. Both Linux and
Windows jobs completed **success**, each with **20 passed tests**.
The printed best N, zero-missing status, and all three SHA256 hashes
were identical on both platforms. The full generated CSV and JSON
were uploaded as workflow artifacts.

## Actual CRAN R package status

A separate job of the same workflow installs the actual R environment,
`cafast>=0.1.1` and `caverify` from CRAN, then independently invokes
`cafast::count_core` and `caverify::ca_verify` on all three CSVs.
This is the real compiled-package acceptance gate; no local R runtime
was installed in the authoring container.

**Do not mark this compiled R gate as passed until its job has
completed successfully** and the `CAFV3741` output lines have been
inspected. Source metadata alone is not execution evidence.

## Engineering findings

- 119 is already below the example t=2 upper bound 125.
- 1288 is already below the example t=3 upper bound 1338.
- 12367 is above the example t=4 upper bound approximately 12354 by 13.
- All bounds are **feasible construction sizes**, not proven global minima.
- Thin interactions are necessary witnesses: removing their unique
  row without replacement invalidates that covered tuple.
- The R compiled counting kernel is intended as a
  verifier/diagnostic/optimizer bridge; existing Python generation
  remains independent, and no GPL code is copied into the repository.

No historical records, private answers, private keys or original
accepted dataset hashes were accessed or changed.
