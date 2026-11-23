"""V3.7.40 unified measured effects of earlier PL5 filter families.

Read ONLY the repository's explicitly labelled synthetic demo. Reuse the
existing BasicConstraint, space indicator registration, pattern filtering,
Boolean filter-mask, and new DSC / recurrence implementations. Never treat
an optimizer, proof auditor or research module as a standalone filter.
"""
from __future__ import annotations

import argparse
import csv
from itertools import combinations
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from .basic_filters import BasicConstraint, apply_basic_filters
from .digit_structure_v3737 import RULES, compile_rule
from .affine_recurrence_filters_v3739 import RULE_NAMES, recurrence_keep_masks
from .engine import UNIVERSE, select_numbers
from .probability_ranker import rank_target_snapshot_v3717
from .multispace import multi_space_study
from .pattern_rules import (Configuration, indicator_table, EXTRA_INDICATORS,
                            indicator_values, filter_next)
from .space_mapping import register_space_indicators
from .legacy_method_census_v3740 import inventory

SCHEMA = "pl5-legacy-filter-unified-matrix-v3740-1"
DOMAIN = 100_000
# These are fixed, outcome-independent parameter-construction methods.
QUANTILES = (0.10, 0.90)
SAMPLE_PERIODS = 8
MAX_GREEDY_RULES = 12


def _hash_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _mask_from_ids(values: np.ndarray) -> int:
    arr = np.asarray(values)
    if arr.ndim != 1 or arr.dtype.kind not in "iu":
        raise ValueError("candidate IDs must be a 1-D integer array")
    if (np.any(arr < 0) or np.any(arr >= DOMAIN)
            or len(np.unique(arr)) != len(arr)):
        raise ValueError("invalid or duplicate candidate IDs")
    mask = np.zeros(DOMAIN, dtype=np.uint8)
    mask[arr] = 1
    return int.from_bytes(np.packbits(mask, bitorder="little").tobytes(), "little")


def _mask_sha256(mask: int) -> str:
    return _hash_bytes(mask.to_bytes((DOMAIN + 7) // 8, "little"))


def _synthetic_records() -> tuple[list[tuple[str, str]], dict]:
    data = Path(__file__).resolve().parent.parent / "data" / "synthetic_demo.csv"
    raw = data.read_bytes()
    decoded = raw.decode("utf-8-sig")
    reader = csv.DictReader(decoded.splitlines())
    if reader.fieldnames != ["period", "number"]:
        raise ValueError("unrecognized synthetic demo schema")
    rows = [(r["period"], r["number"]) for r in reader]
    if len(rows) < 50 or any(
        not issue.isascii() or not issue.isdigit()
        or not number.isascii() or len(number) != 5 or not number.isdigit()
        for issue, number in rows
    ) or any(int(a[0]) >= int(b[0]) for a, b in zip(rows, rows[1:])):
        raise ValueError("invalid synthetic time sequence")
    return rows, {
        "source_kind": "INTERNAL_SYNTHETIC_DEMO_NOT_AUTHENTICATED_HISTORY",
        "source_path": "data/synthetic_demo.csv",
        "source_sha256": _hash_bytes(raw),
        "row_count": len(rows),
        "first_issue": rows[0][0],
        "last_issue": rows[-1][0],
    }


def _mask_summary(name: str, group: str, mask: int,
                  demo: np.ndarray, **metadata) -> dict:
    n = mask.bit_count()
    contains = sum((mask >> int(d)) & 1 for d in demo)
    return {
        "name": name, "family": group,
        "kept_count": n, "excluded_count": DOMAIN - n,
        "candidate_mask_sha256": _mask_sha256(mask),
        "demo_contained": int(contains),
        "demo_evaluated": len(demo),
        "demo_containment_ratio": {
            "numerator": int(contains), "denominator": len(demo)
        },
        "finite_domain_keep_fraction": {
            "numerator": n, "denominator": DOMAIN
        },
        **metadata,
    }


def _indicator_rules(demo: np.ndarray) -> tuple[list[dict], list[tuple[str, int]]]:
    register_space_indicators()
    # Ignore externally registered third-party/test indicators. Freeze the
    # catalog to the existing basic table and the three declared mappings,
    # regardless of test collection order or any process-global registrations.
    prefixes = ("pick23_6__", "pick41_4__", "ternary11__")
    features = {**indicator_table(), **{
        key: value for key, value in EXTRA_INDICATORS.items()
        if key.startswith(prefixes)
    }}
    rows: list[dict] = []
    masks: list[tuple[str, int]] = []
    for name in sorted(features):
        values = np.asarray(indicator_values(name, "raw"))
        if values.shape != (DOMAIN,) or values.dtype.kind not in "iu":
            raise ValueError(f"invalid indicator array: {name}")
        lo, hi = [int(x) for x in np.quantile(values, QUANTILES, method="nearest")]
        # Invoke the ACTUAL existing basic filter implementation; never
        # silently replace it with an unrelated scoring engine.
        selected = apply_basic_filters([
            BasicConstraint(name, minimum=lo, maximum=hi)
        ])
        mask = _mask_from_ids(selected)
        if len(selected) != int(np.count_nonzero((values >= lo) & (values <= hi))):
            raise AssertionError("legacy BasicConstraint disagrees with raw indicator")
        family = "mapped_static" if "__" in name else "basic_static"
        rows.append(_mask_summary(
            f"legacy.{name}.central_quantile_band", family, mask, demo,
            adapter="BasicConstraint", threshold_source="FULL_DOMAIN_QUANTILES_NOT_DEMO",
            minimum=lo, maximum=hi, source_indicator=name,
        ))
        masks.append((f"legacy.{name}", mask))
    return rows, masks


def _structure_rules(demo: np.ndarray) -> tuple[list[dict], list[tuple[str, int]]]:
    rows = []
    masks = []
    for rule in RULES:
        mask = compile_rule(rule)
        name = f"dsc.{rule.name}"
        rows.append(_mask_summary(
            name, "dsc_structure", mask, demo, adapter="StructuralRule",
            feature=rule.feature, comparator=rule.operator, threshold=rule.threshold,
        ))
        masks.append((name, mask))
    for name, mask in zip(RULE_NAMES, recurrence_keep_masks()):
        label = f"modular_recurrence.{name}"
        rows.append(_mask_summary(
            label, "affine_recurrence", mask, demo,
            adapter="recurrence_keep_masks", threshold_source="EXACT_MOD10_EQUATION",
        ))
        masks.append((label, mask))
    return rows, masks


def _time_forward_pattern_matrix(rows: list[tuple[str, str]]) -> list[dict]:
    """Test each target after freezing a model with only prior demo rows."""
    # Keep a small declared job budget. Each call scans 100000 candidates.
    specs = (
        ("legacy.digit5_pattern", ("digit_5",),
         ("constant", "arithmetic", "period2")),
        ("legacy.traditional_pattern", ("sum", "span", "odd_count"),
         ("constant", "arithmetic", "period2")),
        ("legacy.context_pattern", ("same_positions_prev", "digit_overlap_prev"),
         ("constant", "arithmetic", "period2")),
        ("legacy.pick23_mapped_pattern", ("pick23_6__sum",),
         ("constant", "arithmetic", "period2")),
        ("legacy.pick41_mapped_pattern", ("pick41_4__span",),
         ("constant", "arithmetic", "period2")),
        ("legacy.ternary_mapped_pattern", ("ternary11__switch_count",),
         ("constant", "arithmetic", "period2")),
    )
    begin = len(rows) - SAMPLE_PERIODS
    if begin < 40:
        raise ValueError("not enough past-only synthetic demo rows")
    by_spec = []
    for name, indicators, patterns in specs:
        config = Configuration(
            indicators=indicators, transforms=("raw",),
            patterns=patterns, windows=(3, 4), mode="continuation",
            max_total_remove=0.9, max_rule_remove=0.65,
            min_keep=1000, max_rules=30,
        )
        runs = []
        for idx in range(begin, len(rows)):
            past = [number for _, number in rows[:idx]]
            actual = int(rows[idx][1])
            result = filter_next(past, config)
            keep = _mask_from_ids(result.kept)
            runs.append({
                "issue": rows[idx][0],
                "past_rows": idx,
                "past_sha256": _hash_bytes(json.dumps(
                    rows[:idx], ensure_ascii=False, separators=(",", ":")
                ).encode("utf8")),
                "retained_count": keep.bit_count(),
                "candidate_sha256": _mask_sha256(keep),
                "synthetic_contained": bool((keep >> actual) & 1),
                "triggered_rules": int(result.triggered),
                "applied_rules": sum(r.status == "applied" for r in result.rules),
            })
        by_spec.append({
            "name": name, "family": "history_pattern",
            "adapter": "pattern_rules.filter_next",
            "configured_indicators": list(indicators),
            "evaluation_periods": len(runs),
            "total_synthetic_contained": sum(int(r["synthetic_contained"]) for r in runs),
            "average_retained_count_numerator": sum(r["retained_count"] for r in runs),
            "average_retained_count_denominator": len(runs),
            "runs": runs,
        })
    return by_spec



def _time_forward_rank_matrix(rows: list[tuple[str, str]]) -> list[dict]:
    """Matched-K=100 chronology-safe subsets from existing ranking engines.

    Actual synthetic demo record is not accessed until all candidate sets
    for that issue have been frozen, including multiple-space ranking.
    """
    methods = ("random", "positional", "pairwise", "ensemble",
               "heuristic_rank", "multispace_rank")
    results = {name: [] for name in methods}
    compact = Configuration(
        indicators=("sum", "span", "digit_5"),
        transforms=("raw",), patterns=("constant", "arithmetic", "period2"),
        windows=(3, 4), min_keep=1000, max_total_remove=0.9,
        max_rules=25,
    )
    spaces = {
        "pl5": ("sum",),
        "pick23_6": ("sum",),
        "pick41_4": ("span",),
        "ternary11": ("switch_count",),
    }
    for idx in range(len(rows) - SAMPLE_PERIODS, len(rows)):
        prefix = [number for _, number in rows[:idx]]
        history_sha = _hash_bytes(json.dumps(
            rows[:idx], ensure_ascii=False, separators=(",", ":")
        ).encode("utf8"))
        frozen = {}
        for j, method in enumerate(methods[:4]):
            picks = select_numbers(prefix, count=100, model=method,
                                   seed=374000 + idx * 17 + j,
                                   use_gate=False).numbers
            frozen[method] = _mask_from_ids(picks)
        rank = rank_target_snapshot_v3717(prefix, compact)
        frozen["heuristic_rank"] = _mask_from_ids(rank.order[:100])
        multi = multi_space_study(
            prefix, spaces, windows=(3, 4),
            patterns=("constant", "arithmetic", "period2"),
            transforms=("raw",), max_rules=12,
        )
        frozen["multispace_rank"] = _mask_from_ids(np.array(
            [int(x) for x in multi.table["number"].head(100)], dtype=np.int32
        ))
        # Do not reveal target before ALL six masks are frozen.
        actual = int(rows[idx][1])
        for method in methods:
            mask = frozen[method]
            if mask.bit_count() != 100:
                raise AssertionError("ranking adapter lost fixed K=100")
            results[method].append({
                "issue": rows[idx][0], "past_rows": idx,
                "past_sha256": history_sha,
                "candidate_sha256": _mask_sha256(mask),
                "retained_count": 100,
                "synthetic_contained": bool((mask >> actual) & 1),
            })
    return [{
        "name": f"legacy.{method}.fixed_k100",
        "family": "history_ranking_fixed_k",
        "adapter": ("multispace.multi_space_study" if method == "multispace_rank"
                    else "probability_ranker.rank_target_snapshot_v3717"
                    if method == "heuristic_rank"
                    else "engine.select_numbers"),
        "evaluation_periods": len(results[method]),
        "fixed_candidate_budget": 100,
        "total_synthetic_contained": sum(
            int(x["synthetic_contained"]) for x in results[method]
        ),
        "runs": results[method],
    } for method in methods]


def _greedy_compression(masks: list[tuple[str, int]]) -> dict:
    """Greedy structural set reduction, never using demo outcomes.

    This is NOT a global optimality certificate. We refuse an empty mask
    and stop after at most 12 chosen rules; all intermediate counts audit.
    """
    active = (1 << DOMAIN) - 1
    selected = []
    remaining = list(range(len(masks)))
    stages = []
    for _ in range(MAX_GREEDY_RULES):
        candidates = [( (active & masks[i][1]).bit_count(), i)
                      for i in remaining]
        feasible = [(n, i) for n, i in candidates
                    if 0 < n < active.bit_count()]
        if not feasible:
            break
        next_count, index = min(feasible, key=lambda x: (x[0], x[1]))
        name, mask = masks[index]
        active &= mask
        remaining.remove(index)
        selected.append(name)
        stages.append({"name": name, "retained": next_count,
                       "mask_sha256": _mask_sha256(active)})
        if next_count <= 100:
            break
    return {
        "method": "LABEL_FREE_MAX_INCREMENTAL_EXCLUSIONS_GREEDY",
        "selected_rules": selected, "stages": stages,
        "retained": active.bit_count(),
        "target_at_most_100_met": 0 < active.bit_count() <= 100,
        "final_mask_sha256": _mask_sha256(active),
        "global_optimum_claim": False,
        "evaluation_budget": MAX_GREEDY_RULES,
        "limitation": "Greedy structural compression does not guarantee globally minimum rules or reliable historical coverage.",
    }


def _minimum_cardinality_certificate(
    masks: list[tuple[str, int]], selected: list[str], *,
    domain_size: int = DOMAIN, target: int = 100,
) -> dict:
    """Exact minimum-rule certificate for a declared <=3-rule witness.

    Enumerate ALL strictly smaller subsets of the frozen mask inventory.
    A zero-size intersection is not a feasible nonempty candidate set.
    This proves only minimum cardinality within these fixed Boolean masks,
    not optimal historical retention or minimum computational cost.
    """
    if not 1 <= target < domain_size or not 1 <= len(selected) <= 3:
        raise ValueError("invalid target or unsupported proof depth")
    if not masks or len({name for name, _ in masks}) != len(masks):
        raise ValueError("missing or duplicate filter names")
    full = (1 << domain_size) - 1
    if any(not isinstance(mask, int) or not 0 <= mask <= full
           for _, mask in masks):
        raise ValueError("out-of-domain or noninteger mask")
    index = dict(masks)
    if len(set(selected)) != len(selected) or any(s not in index for s in selected):
        raise ValueError("unknown or repeated witness filter")
    witness = full
    for name in selected:
        witness &= index[name]
    witness_count = witness.bit_count()
    if not 0 < witness_count <= target:
        raise ValueError("proposed witness does not meet nonempty target")

    breakdown = []
    first_smaller = None
    total = 0
    for rule_count in range(len(selected)):
        evaluated = zero = positive = 0
        smallest_positive = None
        for subset in combinations(range(len(masks)), rule_count):
            active = full
            for i in subset:
                active &= masks[i][1]
            kept = active.bit_count()
            evaluated += 1
            if kept == 0:
                zero += 1
                continue
            positive += 1
            smallest_positive = (kept if smallest_positive is None
                                 else min(smallest_positive, kept))
            if kept <= target and first_smaller is None:
                first_smaller = {
                    "rule_count": rule_count,
                    "names": [masks[i][0] for i in subset],
                    "retained": kept,
                    "mask_sha256": _hash_bytes(active.to_bytes(
                        (domain_size + 7) // 8, "little")),
                }
        total += evaluated
        breakdown.append({
            "rule_count": rule_count,
            "subsets_examined": evaluated,
            "empty_intersections": zero,
            "nonempty_intersections": positive,
            "minimum_nonempty_retained": smallest_positive,
        })
    return {
        "schema": "pl5-exact-minimum-filter-cardinality-v3741-1",
        "available_frozen_rules": len(masks),
        "target_positive_at_most": target,
        "witness_rules": list(selected),
        "witness_count": witness_count,
        "witness_sha256": _hash_bytes(witness.to_bytes(
            (domain_size + 7) // 8, "little")),
        "strictly_smaller_subsets_examined": total,
        "smaller_cardinality_audit": breakdown,
        "first_smaller_feasible_witness": first_smaller,
        "certified_minimum_rule_count": (
            len(selected) if first_smaller is None else first_smaller["rule_count"]
        ),
        "is_proposed_witness_cardinality_minimal": first_smaller is None,
        "proof_scope": "FROZEN_BOOLEAN_MASK_LIBRARY_ONLY; POSITIVE_CANDIDATE_COUNT_REQUIRED",
        "historical_coverage_measured": False,
        "global_cost_optimality_claim": False,
    }


def run() -> dict:
    census = inventory()
    rows, source = _synthetic_records()
    demo = np.fromiter((int(x[1]) for x in rows), dtype=np.int32)
    legacy, old_masks = _indicator_rules(demo)
    structural, new_masks = _structure_rules(demo)
    static = legacy + structural
    names = [r["name"] for r in static]
    if len(names) != len(set(names)):
        raise AssertionError("duplicate method name in unified matrix")
    pattern = _time_forward_pattern_matrix(rows)
    rank = _time_forward_rank_matrix(rows)
    full_inventory = census["source_rows"]
    # Categorize every source module, but never fabricate missing historical
    # evidence or pretend a meta-optimizer is a direct Boolean filter.
    unsupported = [{
        "module": x["name"], "role": x["role"],
        "reason": ("REQUIRES_AUTHENTIC_EXTERNAL_CONTEXT" if x["external_data_or_custody_required"]
                   else "SEPARATE_COMPONENT_CONTRACT_NOT_A_SINGLE_STATIC_KEEP_MASK")
    } for x in full_inventory if not x["direct_mask_adapter_in_v3740"]]
    combined_masks = old_masks + new_masks
    greedy = _greedy_compression(combined_masks)
    proof = _minimum_cardinality_certificate(combined_masks, greedy["selected_rules"])
    if (proof["witness_count"] != greedy["retained"]
            or proof["witness_sha256"] != greedy["final_mask_sha256"]):
        raise AssertionError("greedy witness disagrees with exact subset auditor")
    return {
        "schema": SCHEMA, "source": source,
        "census": census, "static_mask_arms": static,
        "static_family_counts": {
            family: sum(x["family"] == family for x in static)
            for family in sorted(set(x["family"] for x in static))
        },
        "time_forward_synthetic_pattern_arms": pattern,
        "time_forward_synthetic_fixed_k_rank_arms": rank,
        "time_forward_history_gate": "PAST_ONLY_INTERNAL_SYNTHETIC",
        "greedy_combination": greedy,
        "minimum_rule_cardinality_certificate": proof,
        "non_direct_filter_components": unsupported,
        "measured_static_arms": len(static),
        "measured_time_forward_pattern_arms": len(pattern),
        "measured_fixed_k_rank_arms": len(rank),
        "source_data_category": "SYNTHETIC_DEVELOPMENT_ONLY",
        "trusted_real_historical_comparison_complete": False,
        "original_historical_digests_changed": False,
        "warnings": [
            "All legacy Python modules are counted, but only compatible candidate-producing methods can be evaluated with a shared mask metric.",
            "Static quantile thresholds depend only on the full 100000-ID domain, not the synthetic demo.",
            "History-conditioned filter rules use only preceding synthetic rows; the last eight rows were not used to set parameters.",
            "This synthetic test is not an authenticated historical retention study.",
            "Existing optimizer and mathematical operator tests run under the separate complete Python CI; they are not equivalent to candidate-set audits.",
            "No optimization for historical inclusion was performed.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="PL5 source-census and full static filter matrix")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("refuse to overwrite earlier audit evidence")
    report = run()
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf8")
    print(json.dumps({
        "output": str(args.output),
        "sha256": _hash_bytes(encoded.encode("utf8")),
        "source_modules": report["census"]["tracked_package_modules"],
        "static_mask_arms": report["measured_static_arms"],
        "time_forward_pattern_arms": report["measured_time_forward_pattern_arms"],
        "fixed_k_rank_arms": report["measured_fixed_k_rank_arms"],
        "static_family_counts": report["static_family_counts"],
        "greedy_kept": report["greedy_combination"]["retained"],
        "certified_minimum_rules": report["minimum_rule_cardinality_certificate"]["certified_minimum_rule_count"],
        "smaller_portfolios_audited": report["minimum_rule_cardinality_certificate"]["strictly_smaller_subsets_examined"],
        "real_historical_comparison_complete": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
