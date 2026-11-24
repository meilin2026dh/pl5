"""V3.7.41: reproducible covering-array bridge for PL5 and CRAN cafast.

Five decimal columns, uniform 10 levels. Strength-t coverage concerns every
choice of t columns and its 10**t tuples, not all five-position identities.
This module reuses the accepted V3.7.13 algebraic t=2/3 generator, extends
the same GF(11) polynomial construction to t=4, then removes only rows whose
all t-way interactions are duplicated. Source and output are independently
verifiable. No historical data or outcome labels are used.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from hashlib import sha256
from itertools import combinations, product
import json
from pathlib import Path
from random import Random

from .covering_arrays_v3713 import generate_pl5_covering_array, audit_interactions

SCHEMA = "pl5-covering-cafast-bridge-v3741-1"
FIELD = 11
LEVELS = 10
COLUMNS = 5
DEFAULT_SEEDS = tuple(range(32))


def _check_strength(strength: int) -> None:
    if type(strength) is not int or strength not in (2, 3, 4):
        raise ValueError("supported covering strengths: 2, 3, 4")


def algebraic_start(strength: int) -> list[str]:
    """Coarsen level 10 of GF(11) to decimal 9; preserve five digits."""
    _check_strength(strength)
    if strength in (2, 3):
        rows = generate_pl5_covering_array(strength)
    else:
        # Same field/polynomial rule as frozen V3.7.13, extended to t=4.
        rows = sorted({
            "".join(str(min(sum(c * pow(x, d, FIELD)
                                for d, c in enumerate(coefficients))
                            % FIELD, LEVELS - 1)) for x in range(COLUMNS))
            for coefficients in product(range(FIELD), repeat=strength)
        })
    if len(rows) != len(set(rows)):
        raise AssertionError("duplicate algebraic rows")
    if audit_interactions(rows, strength)["missing"] != 0:
        raise AssertionError("unverified algebraic covering array")
    return sorted(rows)


def _tuple_ids(row: str, colsets: tuple[tuple[int, ...], ...],
               strength: int) -> tuple[int, ...]:
    # Prefix by column-set ID; this makes all t-way requirements distinct.
    return tuple(
        i * (LEVELS ** strength) +
        sum(int(row[j]) * LEVELS ** (strength - p - 1)
            for p, j in enumerate(cols))
        for i, cols in enumerate(colsets)
    )


def verify_counts(rows: list[str], strength: int) -> dict:
    """Exact independent occurrence-frequency coverage check and thin tuples."""
    _check_strength(strength)
    if (not isinstance(rows, list) or len(rows) != len(set(rows))
            or any(type(s) is not str or len(s) != COLUMNS
                   or not s.isascii() or not s.isdecimal() for s in rows)):
        raise ValueError("unique ASCII five-digit rows required")
    colsets = tuple(combinations(range(COLUMNS), strength))
    required = len(colsets) * LEVELS ** strength
    count = Counter(x for row in rows for x in _tuple_ids(row, colsets, strength))
    missing = required - len(count)
    if missing < 0:
        raise AssertionError("tuple index collision")
    return {
        "strength": strength, "rows": len(rows),
        "required_tuples": required, "covered_tuples": len(count),
        "missing_tuples": missing,
        "thin_tuples_covered_once": sum(v == 1 for v in count.values()),
        "minimum_multiplicity": min(count.values()) if count else 0,
        "full_coverage": missing == 0,
    }


def prune_once(rows: list[str], strength: int, seed: int) -> list[str]:
    """One seeded randomized deletion pass; every removal is certified.

    Counts are decremented ONLY when all covered interactions currently
    have multiplicity >1. This preserves full coverage as an invariant.
    Never mutate original input; no addition/replacement of identities.
    """
    _check_strength(strength)
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    checked = verify_counts(rows, strength)
    if not checked["full_coverage"]:
        raise ValueError("initial input is not a covering array")
    colsets = tuple(combinations(range(COLUMNS), strength))
    row_ids = [_tuple_ids(row, colsets, strength) for row in rows]
    frequencies = Counter(x for ids in row_ids for x in ids)
    order = list(range(len(rows)))
    Random(seed).shuffle(order)
    keep = [True] * len(rows)
    for index in order:
        if all(frequencies[tuple_id] > 1 for tuple_id in row_ids[index]):
            keep[index] = False
            for tuple_id in row_ids[index]:
                frequencies[tuple_id] -= 1
    output = [row for i, row in enumerate(rows) if keep[i]]
    result = verify_counts(output, strength)
    if not result["full_coverage"]:
        raise AssertionError("pruning lost a required tuple")
    return output


def experiment(strength: int, seeds: tuple[int, ...] = DEFAULT_SEEDS
               ) -> tuple[list[str], dict]:
    _check_strength(strength)
    if (not isinstance(seeds, tuple) or not seeds
            or any(type(s) is not int or s < 0 for s in seeds)
            or len(set(seeds)) != len(seeds)):
        raise ValueError("seeds must be unique nonnegative integers")
    start = algebraic_start(strength)
    trials = []
    best = None
    winner = None
    for seed in seeds:
        candidate = prune_once(start, strength, seed)
        trials.append({"seed": seed, "rows": len(candidate)})
        if best is None or (len(candidate), seed) < (len(best), winner):
            best, winner = candidate, seed
    assert best is not None and winner is not None
    audit = verify_counts(best, strength)
    legacy = audit_interactions(best, strength)
    if legacy["missing"] != audit["missing_tuples"]:
        raise AssertionError("independent legacy verifier disagrees")
    digest = sha256(("\n".join(best) + "\n").encode("ascii")).hexdigest()
    return best, {
        "schema": SCHEMA,
        "strength": strength,
        "number_of_positions": COLUMNS,
        "digit_levels": LEVELS,
        "construction": "GF11_POLYNOMIAL_LEVEL10_COARSEN_TO9",
        "original_algebraic_rows": len(start),
        "restarts": len(seeds),
        "trials": trials,
        "selected_seed": winner,
        "best_row_sha256": digest,
        "required_tuples": audit["required_tuples"],
        "missing_tuples": audit["missing_tuples"],
        "thin_tuples": audit["thin_tuples_covered_once"],
        "best_rows": len(best),
        "simple_theoretical_lower_bound": LEVELS ** strength,
        "construction_is_proven_minimum": False,
        "historical_data_read": False,
        "external_r_cafast_executed": False,
        "note": "Rows are a digit-interaction cover; this does not cover every full five-digit identifier.",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="PL5 covering-array reference experiment")
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--restarts", type=int, default=32)
    args = ap.parse_args()
    if args.restarts < 1 or args.restarts > 64:
        raise ValueError("restarts must be 1..64")
    outdir = args.outdir
    if outdir.exists():
        raise FileExistsError("refuse to replace existing audit output")
    outdir.mkdir(parents=True, exist_ok=False)
    records = []
    for t in (2, 3, 4):
        rows, report = experiment(t, tuple(range(args.restarts)))
        path = outdir / f"CA_5x10_t{t}.csv"
        with path.open("w", encoding="ascii", newline="") as f:
            csv.writer(f).writerows([list(map(int, r)) for r in rows])
        records.append(report)
    blob = json.dumps(records, indent=2, sort_keys=True) + "\n"
    (outdir / "summary.json").write_text(blob, encoding="utf8")
    print(json.dumps({
        "results": [{"t": r["strength"], "N": r["best_rows"],
                     "missing": r["missing_tuples"], "sha256": r["best_row_sha256"]}
                    for r in records],
        "output": str(outdir),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
