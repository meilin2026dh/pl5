"""V3.7.44: exact minimal-conflict certificates for frozen filter candidates.

Audit fixed K=100 subsets from the existing V3.7.43 24-window ledger.
Candidate membership and frozen source hashes are the *only* inputs to
combination calculations. No target row is consulted by the audit itself.

Bitwise AND generates all 2**6-1 subset certificates; independent direct
set intersections verify every retained count and 100,000-bit SHA256.
This is an engineering compatibility audit, not an efficacy ranking.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from .filter_fair_longitudinal_v3743 import (
    DOMAIN, K, METHODS, SCHEMA as SOURCE_SCHEMA, verify_longitudinal,
)

SCHEMA = "pl5-frozen-filter-conflicts-v3744-1"
FULL_MASK = (1 << DOMAIN) - 1
BYTE_WIDTH = (DOMAIN + 7) // 8
METHOD_COUNT = len(METHODS)
ALL_MASK = (1 << METHOD_COUNT) - 1
PAIR_COUNT = METHOD_COUNT * (METHOD_COUNT - 1) // 2


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf8")


def _digest(value: object) -> str:
    return sha256(_canonical(value)).hexdigest()


def _mask_hash(bits: int) -> str:
    return sha256(bits.to_bytes(BYTE_WIDTH, "little")).hexdigest()


def _bits(ids: list[str]) -> int:
    out = 0
    for candidate in ids:
        out |= 1 << int(candidate)
    return out


def _minimal_cores(counts: dict[int, int]) -> list[int]:
    """In a monotone AND lattice, immediate-parent nonempty is sufficient."""
    all_masks = set(range(1, ALL_MASK + 1))
    if set(counts) != all_masks or any(type(n) is not int or n < 0 or n > DOMAIN
                                      for n in counts.values()):
        raise ValueError("complete nonnegative subset lattice required")
    result = []
    for mask in sorted(counts):
        if mask.bit_count() < 2 or counts[mask]:
            continue
        if all(counts[mask ^ (1 << i)] > 0 for i in range(METHOD_COUNT)
               if mask & (1 << i)):
            result.append(mask)
    return result


def _bitwise_window(record: dict) -> dict:
    methods = record["panel"]["payload"]["methods"]
    bitsets = [_bits(arm["candidate_ids"]) for arm in methods]
    certs = []
    counts = {}
    for subset_mask in range(1, ALL_MASK + 1):
        intersect = FULL_MASK
        for i, bits in enumerate(bitsets):
            if subset_mask & (1 << i):
                intersect &= bits
        count = intersect.bit_count()
        counts[subset_mask] = count
        certs.append({
            "subset_mask": subset_mask,
            "retained_count": count,
            "candidate_bitmap_sha256": _mask_hash(intersect),
        })
    return _window_record(record, certs, counts)


def _independent_set_window(record: dict) -> dict:
    """Verifier oracle uses sets + bytearray, not the builder's int masks."""
    methods = record["panel"]["payload"]["methods"]
    candidate_sets = [set(arm["candidate_ids"]) for arm in methods]
    certs = []
    counts = {}
    for subset_mask in range(1, ALL_MASK + 1):
        chosen = [candidate_sets[i] for i in range(METHOD_COUNT)
                  if subset_mask & (1 << i)]
        common = set.intersection(*chosen)
        bitmap = bytearray(BYTE_WIDTH)
        for candidate in common:
            index = int(candidate)
            bitmap[index // 8] |= 1 << (index % 8)
        counts[subset_mask] = len(common)
        certs.append({
            "subset_mask": subset_mask,
            "retained_count": len(common),
            "candidate_bitmap_sha256": sha256(bitmap).hexdigest(),
        })
    return _window_record(record, certs, counts)


def _window_record(record: dict, certs: list[dict], counts: dict[int, int]) -> dict:
    cores = _minimal_cores(counts)
    return {
        "issue": record["issue"],
        "frozen_panel_sha256": record["panel"]["payload_sha256"],
        "subset_certificates": certs,
        "minimal_conflict_masks": cores,
        "zero_pair_count": sum(counts[mask] == 0 for mask in counts
                               if mask.bit_count() == 2),
        "max_nonempty_subset_size": max(mask.bit_count() for mask, count
                                        in counts.items() if count > 0),
    }


def _assemble(source: dict, windows: list[dict]) -> dict:
    by_size = Counter(mask.bit_count() for window in windows
                      for mask in window["minimal_conflict_masks"])
    return {
        "schema": SCHEMA,
        "frozen_source_schema": SOURCE_SCHEMA,
        "frozen_source_canonical_sha256": _digest(source),
        "frozen_source_chain_sha256": source["final_chain_sha256"],
        "frozen_dataset_sha256": source["dataset_raw_sha256"],
        "source_evidence_class": source["evidence_class"],
        "universe_size": DOMAIN,
        "candidate_budget_per_method": K,
        "method_order": list(METHODS),
        "window_count": len(windows),
        "subset_count_per_window": ALL_MASK,
        "windows": windows,
        "summary": {
            "pairwise_comparisons": len(windows) * PAIR_COUNT,
            "pairwise_empty_intersections": sum(w["zero_pair_count"] for w in windows),
            "six_way_empty_windows": sum(
                w["subset_certificates"][-1]["retained_count"] == 0
                for w in windows),
            "minimal_conflicts_by_size": {
                str(i): by_size.get(i, 0) for i in range(2, METHOD_COUNT + 1)
            },
            "windows_with_genuine_three_way_minimal_conflict": sum(
                any(mask.bit_count() == 3 for mask in w["minimal_conflict_masks"])
                for w in windows),
        },
        "uses_observed_ids_for_combination_calculation": False,
        "independent_historical_performance_claim": False,
    }


def build_conflict_certificates(source: dict) -> dict:
    """Exact K-matched filter-intersection audit using frozen candidates."""
    verify_longitudinal(source)
    if source["evidence_class"] != "INTERNAL_SYNTHETIC":
        raise ValueError("unapproved evidence class")
    windows = [_bitwise_window(record) for record in source["records"]]
    result = _assemble(source, windows)
    verify_conflict_certificates(source, result)
    return result


def verify_conflict_certificates(source: dict, certificate: object) -> None:
    """Independent complete-set oracle checks every subset and root digest."""
    verify_longitudinal(source)
    if not isinstance(certificate, dict):
        raise ValueError("expected certificate mapping")
    expected = _assemble(
        source, [_independent_set_window(record) for record in source["records"]]
    )
    if certificate != expected:
        raise ValueError("source/combination certificate mismatch")


def main() -> None:
    """Read a frozen V3.7.43 JSON; refuse to overwrite audit outputs."""
    import argparse
    parser = argparse.ArgumentParser(description="Exact PL5 K=100 candidate-intersection certificates")
    parser.add_argument("--frozen-input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.frozen_input.read_text(encoding="utf8"))
    result = build_conflict_certificates(source)
    encoded = json.dumps(result, sort_keys=True, indent=2,
                         ensure_ascii=False, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf8") as file:
        file.write(encoded)
    print(json.dumps({
        "output_sha256": sha256(encoded.encode("utf8")).hexdigest(),
        "frozen_source_chain_sha256": result["frozen_source_chain_sha256"],
        "window_count": result["window_count"],
        "summary": result["summary"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
