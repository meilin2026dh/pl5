# PL5 V3.7.45 — Exact maximum-compatible filtering family and minimum relaxation

## Single falsifiable engineering question

Given six fixed K=100 membership masks from the previously audited V3.7.43 synthetic 24-window ledger, each drawn from 100000 five-digit identities, how many filtering methods can be *jointly imposed by intersection* without producing an empty candidate set? When the full six-way intersection is empty, what is the **minimum number of methods that must be relaxed**?

Define S(M) as the intersection of frozen keep sets selected by binary mask M, for all 63 nonempty subsets. A feasible family is one with |S(M)| > 0. The exact maximum joint method count is k* = max popcount(M) over all feasible M. The minimum number of relaxed methods is exactly 6-k*. This is a finite combinatorial certificate, not a heuristic.

Enumerate **all** maximum-cardinality compatible method masks. The deterministic output chooses first by fewest remaining candidate identities, then by smallest integer mask. It also records each blocked attempt to add an omitted method, the chosen full-bitset SHA256 and the input experiment chain and SHA256. Every chosen set remains <= 100 identities because each source method has K=100.

## Falsification and independent verification

The builder reads **only the complete 63-subset intersection count and bitmap hash table** from the V3.7.44 certificates (after verifying them against the frozen V3.7.43 source). An independent verifier reconstructs all 63 intersections directly from the frozen candidate lists using Python set operations and recomputes chosen-set bitmap SHA256 with an independent bytearray representation. Tampering, missing subsets, nonmonotone counts, changed input-source hashes or altered selection masks fail closed.

This audit does not read observed window identities to select a family. The preserved source is *INTERNAL_SYNTHETIC development only*. It does not establish actual historical coverage, future containment, effectiveness, or cross-window optimum under policy selection. Choosing a different compatible family independently for each window is an engineering compatibility diagnostic, not a deployed longitudinal filtering policy.

The chosen objective is **maximum number of jointly compatible fixed methods**, not lowest wall-time or cheapest short-circuit execution. More imposed methods need not be better on any external validation. The certificate permits comparing meaningful nonempty portfolios to the previous all-six empty-intersection negative result without changing any rule definition or source data.

## Reproduction

From pl5-cumulative/research_backend:

- python -m pytest -q tests/test_filter_compatible_repairs_v3745.py tests/test_filter_conflict_certificates_v3744.py
- python -m pailie5.filter_fair_longitudinal_v3743 --output ../../ci-results/v3745-frozen-local.json
- python -m pailie5.filter_conflict_certificates_v3744 --frozen-input ../../ci-results/v3745-frozen-local.json --output ../../ci-results/v3745-conflicts-local.json
- python -m pailie5.filter_compatible_repairs_v3745 --frozen-input ../../ci-results/v3745-frozen-local.json --conflict-input ../../ci-results/v3745-conflicts-local.json --output ../../ci-results/v3745-repairs-local.json

Outputs open with exclusive creation, never overwrite existing evidence. Dedicated Ubuntu and Windows Python 3.12 GitHub Actions preserve all three complete outputs. Cross-platform identical JSON and all relevant gates are prerequisites for focused acceptance. Full clean-machine and application checks are separate. Keep this work in the isolated draft PR, do not modify main.

**Research classification:** fixed-set structural engineering only, with reproducibility and negative results retained. No historical source archives, data hashes, restricted records or keys modified.
