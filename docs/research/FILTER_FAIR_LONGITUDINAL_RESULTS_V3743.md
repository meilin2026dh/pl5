# PL5 V3.7.43 actual 24-window equal-K synthetic experiment

## Completed reproducible engineering checks

- Code revision: `52fd4e7e2ce3db324c2bb293ae43101a0b599b4e`.
- [GitHub Actions run #45223203269](https://github.com/meilin2026dh/pl5/actions/runs/45223203269)
  **passed** the full V3.7.43 matrix on Python 3.12 Ubuntu and Windows.
- Both OS jobs reported **21/21 targeted tests passed** and executed
  the full 24-window source-frozen experiment.
- Full serialized JSON SHA256 **identical on both platforms**:
  `38be27540646429ef3b355492bc868bb5851d4c1f0fde8fe46d7eb2d5a195577`.
- Chained final experiment ledger SHA256 identical:
  `6b9f96e6f1a4f38b60f7ca1f50d927e63049c8da8a22ccf253bdbcd76727ecd3`.
- Input raw synthetic-demo SHA256:
  `f7812094b6a4c7f6a8b10676c1b6ab95e3a234efdede9ff2786319a2fefc6ff6`.
- Each complete JSON report is preserved as a downloadable CI artifact.
  The JSON includes the *entire frozen candidate set* for each method
  and issue, all code/parameter digests, every result and the chain.

## Result from all 24 equally budgeted windows

Each method retained K=100 of all 100,000 possible five-digit IDs
per evaluation record, with 976 training synthetic records before the
first evaluated window.

| Previously implemented method | Synthetic records contained / 24 | Synthetic records excluded / 24 |
|---|---:|---:|
| Existing combined statistics | 0 | 24 |
| Existing paired-position statistics | 0 | 24 |
| Existing position-wise statistics | 0 | 24 |
| Existing heuristic ranking | 0 | 24 |
| Existing modular-recurrence structure | 0 | 24 |
| Seeded uniform 100-ID control | 0 | 24 |

**Interpretation: no ranking is supported by these counts.** Under
independently uniform synthetic identities and K=100, the expected
number of retained records for a 24-record window is only
`24*100/100000=0.024` per method; observing zero is commonplace.
These are synthetic development data, not authenticated
real historical data. Comparing false-exclusion counts of 24 for
every method establishes no unique advantage or deficiency.

## New engineering capability

- Existing V3.7.42 source-verified full 100000-bit frozen payloads are
  now produced and evaluated for all six adapters across **24** windows.
- Every evaluation uses **only preceding rows** to construct the
  selected candidates. The target value is passed only to the
  later settlement stage of that issue.
- Every settlement explicitly contains the actual reserved
  synthetic ID, enabling the V3.7.43 verifier to recompute membership
  from the complete frozen candidate list independently.
- SHA256 ledger chaining detects missing/reordered/tampered records,
  wrong K and changed summary totals; original training and source
  digests are preserved.
- Both platforms generated identical complete JSON bytes.

## Boundaries and next research work

1. **This is not all prior PL5 methods.** V3.7.40 catalogued 97 source
   modules and exercised 70 comparable filtering configurations;
   this particular *multi-window equal-K* pilot uses six inherited
   candidate-producing adapters. More adapters are needed before any
   whole-library fairness claim.
2. 24 windows at K=100 are too few for a meaningful comparison of
   rare retained memberships. A larger **authenticated historical**
   dataset and a frozen time-window policy would be necessary.
3. The SHA chain is content integrity evidence, not trusted external
   creation time, third-party authorship, or a tamper-proof system
   against an attacker able to replace both data and root hash.
4. No machine-time comparison or memory benchmark is included.
   Identical K does not imply equivalent computational cost.
5. The next engineering questions are pairwise mask overlap,
   duplicate exclusions, stability of candidate sets across
   adjacent windows and complete method coverage. Those can be
   studied directly from the frozen full-bitmaps without any
   new historical data access.

No changes to original historical source bytes, accepted hashes,
secrets or `main`.


## Full-candidate structural complementarity (independently inspected)

The unchanged **24-window frozen full-membership JSON** from the
successful cross-platform run #45223203269 was downloaded as a GitHub
Actions artifact. We recomputed exact pairwise set intersections,
same-method adjacent-window intersections and six-method unions
independently from the serialized candidate IDs. These checks do not
inspect any synthetic target values.

### Distinct methods: intersection sizes at fixed K=100

| Pair of methods | Mean exact common identities / window |
|---|---:|
| Existing ensemble vs pairwise statistics | **56.625** |
| Existing ensemble vs positional statistics | **16.000** |
| Existing pairwise vs positional statistics | **1.750** |
| Existing heuristic rank vs modular recurrence | **0.9583** |
| Any other pair | **0 to 0.167** |

Across all 24 windows, taking the union of the six K=100 sets
gives a mean of **526.0833 distinct IDs**, minimum **524**,
maximum **530**, compared with 600 positions before deduplication.
This describes structural overlap, not historical containment.

### Within-method adjacent-window membership stability

| Method | Mean common retained identities across consecutive windows (out of 100) |
|---|---:|
| Ensemble statistics | 96.9130 |
| Pairwise statistics | 98.0000 |
| Positional statistics | 93.9565 |
| Heuristic full-space rank | 96.7826 |
| Modular recurrence | 100.0000 |
| Seeded uniform control | 0.0435 |

The fixed mathematical recurrence mask is, as expected, identical
across windows. The random control changes almost completely under
the per-issue frozen seed schedule. Other methods exhibit high overlap
in these 24 synthetic periods. These are **observed facts about the
method-generated sets**, not evidence that more stable sets are more
effective. Different seeds, sample windows or rule settings can change
these numbers.

A follow-up code change `filter_fair_longitudinal_v3743.py` exposes
these exact membership-only diagnostics as part of the compact CLI
summary, with independent tests for bounds, pair-count and stable
recurrence membership. Its own new-head CI must be checked
separately before declaring that update accepted.
