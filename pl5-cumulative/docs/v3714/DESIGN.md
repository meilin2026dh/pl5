# V3.7.14 — PL5 high-throughput filtering engine

## Purpose
Integrate high-throughput, *exact* filtering for the PL5 fixed universe of 100,000 integer-coded tickets while preserving existing rule semantics. A Bloom filter is deliberately not used for the 100,000-element universe, where a 12.5 KB exact bitset is practical and has zero false positives.

## Existing baseline
`research_backend/pailie5/basic_filters.py` implements vectorized NumPy filtering with `BasicConstraint`; it is the authoritative comparison oracle for conjunctions. Prior V3.7.13 covering arrays, codebook and conformal-risk modules remain unchanged.

## Architecture
New module `pailie5/high_throughput_v3714.py` offers lazy exact bitmap compilation, per-rule cached integers, AND/OR/NOT combination, trusted deferred predicates for expensive evaluations, explicit cache invalidation by dependency, rule replacement, and counters.

## Tradeoffs
A Bloom accelerator requires a pre-built membership set and can generate false positives. A direct cached bitmap permits exact membership and boolean composition for 100,000 elements. A vectorized NumPy baseline may still beat the bitmap for a single cold query, so benchmarks must report both cold and warm costs instead of claiming unconditional speedups.

## Guarantees and limitations
- Every cached mask has exactly 100,000 positions; ticket indices correspond to 00000–99999, including leading zeroes.
- Expensive deferred predicates may appear only in `all_of`; they cannot be cached without proof that their context stays fixed. Deferred predicates operate only on bitmap survivors.
- Replacing or removing a rule invalidates its cached mask. Rules dependent on external context must be explicitly invalidated when that context changes.
- No implicit randomness, lottery-performance claim, or hit-probability claim.
- Benchmark compares exact outputs against the current NumPy implementation; no guarantee of faster cold construction.

## Deliverables
Complete cumulative source ZIP; module, tests and CLI, reproducible benchmark script, JSON evidence and Chinese report; GitHub research branch sync when possible.
