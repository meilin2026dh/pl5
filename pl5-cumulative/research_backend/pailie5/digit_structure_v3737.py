"""V3.7.37: five-digit structural feature operators and exact filter increment audit.

Pure structural filter engineering. A five-digit tuple is NOT a meaningful
sample for long-stream statistical-test p-values; these are deterministic
functions of the entire 00000..99999 domain. No historical records are read.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from functools import lru_cache
from typing import Mapping

import numpy as np

from .engine import DIGITS

DOMAIN = 100_000
SCHEMA = "pl5-digit-structure-v3737-1"
FEATURES = ("mod10_curvature_zeros", "mod10_delta_distinct", "lag2_matches")
OPERATORS = ("eq", "le", "ge")


@dataclass(frozen=True)
class StructuralRule:
    name: str
    feature: str
    operator: str
    threshold: int

    def __post_init__(self) -> None:
        if (not isinstance(self.name, str) or not self.name
                or self.feature not in FEATURES
                or self.operator not in OPERATORS
                or type(self.threshold) is not int):
            raise ValueError("invalid registered structural rule")


# Fixed, developer-authored structural hypotheses. A True in the
# compiled mask means KEEP. Nothing is tuned against historical results.
RULES = (
    StructuralRule("exclude_mod10_arithmetic", "mod10_curvature_zeros", "eq", 3),
    StructuralRule("exclude_exact_period2", "lag2_matches", "eq", 3),
    StructuralRule("exclude_low_delta_diversity", "mod10_delta_distinct", "le", 2),
    StructuralRule("exclude_near_period2", "lag2_matches", "ge", 2),
    StructuralRule("exclude_nonzero_mod10_arithmetic", "mod10_curvature_zeros", "eq", 3),
)


def _bits(arr: np.ndarray) -> int:
    a = np.asarray(arr)
    if a.shape != (DOMAIN,) or a.dtype != np.dtype("bool"):
        raise ValueError("mask must be exactly 100000 booleans")
    return int.from_bytes(np.packbits(a, bitorder="little").tobytes(), "little")


def _hash(mask: int) -> str:
    return sha256(mask.to_bytes((DOMAIN + 7) // 8, "little")).hexdigest()


@lru_cache(maxsize=1)
def feature_table() -> Mapping[str, np.ndarray]:
    """Enumerate all tuples once; returned feature arrays are read-only."""
    digits = np.asarray(DIGITS, dtype=np.int16)
    if digits.shape != (DOMAIN, 5):
        raise ValueError("unexpected five-digit identity universe")
    delta = (digits[:, 1:] - digits[:, :-1]) % 10
    curvature = (delta[:, 1:] - delta[:, :-1]) % 10
    distinct = np.ones(DOMAIN, dtype=np.int16)
    for j in range(1, 4):
        distinct += ~np.any(delta[:, j:j+1] == delta[:, :j], axis=1)
    result = {
        "mod10_curvature_zeros": np.sum(curvature == 0, axis=1).astype(np.int16),
        "mod10_delta_distinct": distinct,
        "lag2_matches": np.sum(digits[:, 2:] == digits[:, :-2], axis=1).astype(np.int16),
    }
    for values in result.values():
        values.flags.writeable = False
    return result


def compile_rule(rule: StructuralRule) -> int:
    """Return exact keep-mask bitset, with one bit per numeric identity."""
    if not isinstance(rule, StructuralRule):
        raise ValueError("registered StructuralRule required")
    values = feature_table()[rule.feature]
    reject = (values == rule.threshold if rule.operator == "eq"
              else values <= rule.threshold if rule.operator == "le"
              else values >= rule.threshold)
    return _bits(~reject)


def reference_baseline() -> int:
    """A fixed illustrative combination of existing sum and span metrics."""
    from .pattern_rules import indicator_table
    features = indicator_table()
    keep = ((features["sum"] >= 10) & (features["sum"] <= 35)
            & (features["span"] >= 3))
    return _bits(keep)


def audit_structural_increment(
    baseline_keep: int, rules: tuple[StructuralRule, ...] = RULES
) -> dict:
    """Exact standalone, overlap and marginal exclusion audit.

    All increments are computed relative to an input frozen baseline.
    Sequential marginal exclusions depend on the frozen rule order; no
    optimization based on historical outcomes is performed.
    """
    full = (1 << DOMAIN) - 1
    if type(baseline_keep) is not int or not 0 <= baseline_keep <= full:
        raise ValueError("baseline must be a valid 100000-bit keep mask")
    if (not isinstance(rules, tuple) or not 1 <= len(rules) <= 12
            or any(not isinstance(r, StructuralRule) for r in rules)
            or len({r.name for r in rules}) != len(rules)):
        raise ValueError("rules must be a tuple of 1..12 unique definitions")
    keep = baseline_keep
    records = []
    for rule in rules:
        rule_keep = compile_rule(rule)
        rejected = full ^ rule_keep
        initial_removed = rejected.bit_count()
        overlap = (rejected & (full ^ baseline_keep)).bit_count()
        incremental = (keep & rejected).bit_count()
        next_keep = keep & rule_keep
        if keep.bit_count() - next_keep.bit_count() != incremental:
            raise AssertionError("increment accounting error")
        records.append({
            "name": rule.name,
            "feature": rule.feature, "operator": rule.operator,
            "threshold": rule.threshold,
            "rule_keep_sha256": _hash(rule_keep),
            "standalone_excluded": initial_removed,
            "overlap_with_baseline_exclusions": overlap,
            "additional_excluded_against_baseline": initial_removed - overlap,
            "additional_excluded_in_sequence": incremental,
            "remaining_after_application": next_keep.bit_count(),
            "zero_marginal_in_sequence": incremental == 0,
        })
        keep = next_keep
    return {
        "schema": SCHEMA,
        "reference": "COMPLETE_ENUMERATION_OF_FIVE_DIGIT_SPACE",
        "baseline_keep_sha256": _hash(baseline_keep),
        "baseline_count": baseline_keep.bit_count(),
        "final_keep_sha256": _hash(keep),
        "final_keep_count": keep.bit_count(),
        "incrementally_removed": baseline_keep.bit_count() - keep.bit_count(),
        "rule_order": [r.name for r in rules],
        "rule_metrics": records,
        "historical_coverage_measured": False,
        "historical_labels_read": False,
        "interpretation": [
            "These are exact deterministic structural filters, not stream-randomness p-values.",
            "A high standalone exclusion count need not add exclusions beyond the previous rules.",
            "All results depend on a frozen rule order and baseline mask; no historical retention is measured.",
        ],
    }
