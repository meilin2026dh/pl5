"""V3.7.45: exact, outcome-blind minimum-relaxation certificates.

Given six frozen K=100 keep sets, find every largest-cardinality family
whose Boolean intersection is nonempty.  Among those families, choose the
smallest surviving set, with a fixed numeric-mask tie break.  The theorem is
finite enumeration of all 63 subsets, not a heuristic or a coverage claim.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from .filter_conflict_certificates_v3744 import (
    ALL_MASK, METHOD_COUNT, SCHEMA as CONFLICT_SCHEMA,
    verify_conflict_certificates,
)
from .filter_fair_longitudinal_v3743 import (
    DOMAIN, K, METHODS, SCHEMA as FROZEN_SCHEMA, verify_longitudinal,
)

SCHEMA = "pl5-exact-compatible-filter-repairs-v3745-1"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf8")


def _sha(value: object) -> str:
    return sha256(_canonical(value)).hexdigest()


def _solve_counts(certs: list[dict]) -> dict:
    """A complete subset lattice is mandatory: no silent missing masks."""
    if not isinstance(certs, list) or len(certs) != ALL_MASK:
        raise ValueError("incomplete intersection lattice")
    count = {}
    digests = {}
    for expected, cert in enumerate(certs, 1):
        if (not isinstance(cert, dict)
                or set(cert) != {"subset_mask", "retained_count",
                                    "candidate_bitmap_sha256"}
                or type(cert["subset_mask"]) is not int
                or cert["subset_mask"] != expected
                or type(cert["retained_count"]) is not int
                or not 0 <= cert["retained_count"] <= K
                or type(cert["candidate_bitmap_sha256"]) is not str
                or len(cert["candidate_bitmap_sha256"]) != 64
                or any(c not in "0123456789abcdef"
                       for c in cert["candidate_bitmap_sha256"])):
            raise ValueError("invalid subset certificate")
        count[expected] = cert["retained_count"]
        digests[expected] = cert["candidate_bitmap_sha256"]
    if any(count[1 << i] != K for i in range(METHOD_COUNT)):
        raise ValueError("single-method K budget mismatch")
    # Inclusion monotonicity is necessary for ANY genuine AND lattice.
    for mask in range(1, ALL_MASK + 1):
        for i in range(METHOD_COUNT):
            if not (mask & (1 << i)) and count[mask | (1 << i)] > count[mask]:
                raise ValueError("nonmonotone intersection counts")
    maximum = max(mask.bit_count() for mask, n in count.items() if n > 0)
    optimum = [mask for mask in count
               if mask.bit_count() == maximum and count[mask] > 0]
    selected = min(optimum, key=lambda m: (count[m], m))
    # Every dropped method is proven incompatible with the selected family.
    blocked = [selected | (1 << i) for i in range(METHOD_COUNT)
               if not selected & (1 << i)]
    if any(count[m] for m in blocked):
        raise AssertionError("maximum-family proof inconsistent")
    return {
        "max_compatible_methods": maximum,
        "min_methods_relaxed": METHOD_COUNT - maximum,
        "all_max_compatible_masks": optimum,
        "chosen_mask": selected,
        "chosen_retained_count": count[selected],
        "chosen_bitmap_sha256": digests[selected],
        "blocked_single_addition_masks": blocked,
        "nonempty_subsets": sum(n > 0 for n in count.values()),
    }


def _assemble(frozen: dict, conflict: dict, windows: list[dict]) -> dict:
    distribution = Counter(r["max_compatible_methods"] for r in windows)
    return {
        "schema": SCHEMA,
        "frozen_source_schema": FROZEN_SCHEMA,
        "conflict_source_schema": CONFLICT_SCHEMA,
        "frozen_source_chain_sha256": frozen["final_chain_sha256"],
        "frozen_dataset_sha256": frozen["dataset_raw_sha256"],
        "conflict_report_sha256": _sha(conflict),
        "evidence_class": frozen["evidence_class"],
        "universe_size": DOMAIN,
        "single_method_candidate_budget": K,
        "methods": list(METHODS),
        "window_count": len(windows),
        "windows": windows,
        "summary": {
            "max_compatible_method_count_histogram": {
                str(i): distribution.get(i, 0)
                for i in range(1, METHOD_COUNT + 1)
            },
            "selected_retained_count_total": sum(
                r["chosen_retained_count"] for r in windows),
            "selected_retained_count_mean_denominator": len(windows),
            "all_six_incompatible_windows": sum(
                r["max_compatible_methods"] < METHOD_COUNT for r in windows),
        },
        "uses_observed_ids_to_choose_portfolio": False,
        "historical_coverage_verified": False,
    }


def build_repair_certificates(frozen: dict, conflict: dict) -> dict:
    verify_conflict_certificates(frozen, conflict)
    windows = []
    for row in conflict["windows"]:
        windows.append({
            "issue": row["issue"],
            "frozen_panel_sha256": row["frozen_panel_sha256"],
            **_solve_counts(row["subset_certificates"]),
        })
    result = _assemble(frozen, conflict, windows)
    verify_repair_certificates(frozen, conflict, result)
    return result


def _independent_windows(frozen: dict, conflict: dict) -> list[dict]:
    """Independent Python-set oracle; does not call _solve_counts."""
    answer = []
    for source, cert in zip(frozen["records"], conflict["windows"]):
        sets = [set(method["candidate_ids"])
                for method in source["panel"]["payload"]["methods"]]
        members = {}
        for mask in range(1, ALL_MASK + 1):
            chosen_sets = [sets[i] for i in range(METHOD_COUNT)
                           if mask & (1 << i)]
            members[mask] = set.intersection(*chosen_sets)
        viable = [mask for mask in members if members[mask]]
        largest = max(mask.bit_count() for mask in viable)
        all_largest = [mask for mask in viable
                       if mask.bit_count() == largest]
        chosen = min(all_largest,
                     key=lambda m: (len(members[m]), m))
        assert all(not members[chosen | (1 << i)]
                   for i in range(METHOD_COUNT)
                   if not chosen & (1 << i))
        bitmap = bytearray((DOMAIN + 7) // 8)
        for value in members[chosen]:
            n = int(value)
            bitmap[n // 8] |= 1 << (n % 8)
        answer.append({
            "issue": source["issue"],
            "frozen_panel_sha256": source["panel"]["payload_sha256"],
            "max_compatible_methods": largest,
            "min_methods_relaxed": METHOD_COUNT - largest,
            "all_max_compatible_masks": all_largest,
            "chosen_mask": chosen,
            "chosen_retained_count": len(members[chosen]),
            "chosen_bitmap_sha256": sha256(bitmap).hexdigest(),
            "blocked_single_addition_masks": [
                chosen | (1 << i) for i in range(METHOD_COUNT)
                if not chosen & (1 << i)
            ],
            "nonempty_subsets": len(viable),
        })
    return answer


def verify_repair_certificates(frozen: dict, conflict: dict,
                               result: object) -> None:
    # Full source and all 1512 subset hashes verified BEFORE comparison.
    verify_conflict_certificates(frozen, conflict)
    if not isinstance(result, dict):
        raise ValueError("repair record must be a JSON object")
    expected = _assemble(frozen, conflict,
                         _independent_windows(frozen, conflict))
    if result != expected:
        raise ValueError("exact compatible-family certificate mismatch")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="Exact minimal filter relaxation, frozen memberships only")
    parser.add_argument("--frozen-input", type=Path, required=True)
    parser.add_argument("--conflict-input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    frozen = json.loads(args.frozen_input.read_text(encoding="utf8"))
    conflict = json.loads(args.conflict_input.read_text(encoding="utf8"))
    result = build_repair_certificates(frozen, conflict)
    encoded = json.dumps(result, sort_keys=True, indent=2,
                         ensure_ascii=False, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf8") as out:
        out.write(encoded)
    print(json.dumps({
        "output_sha256": sha256(encoded.encode("utf8")).hexdigest(),
        "frozen_source_chain_sha256":
            result["frozen_source_chain_sha256"],
        "summary": result["summary"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
