"""V3.7.13 PL5 one-hot multi-constant-weight codes and dispersion selection.

All five-digit PL5 identifiers map to binary length=50 and weight=5.
Merely being constant-weight is a *vacuous* constraint here; dispersion
requires a separate minimum q-ary Hamming distance (binary distance = 2*d).
"""
from __future__ import annotations

from itertools import combinations
from .covering_arrays_v3713 import _validate_numbers, audit_interactions
from .number_validation import is_five_digit_draw


def encode_one_hot(number: str) -> tuple[int, ...]:
    if not is_five_digit_draw(number):
        raise ValueError('PL5 number must have exactly five ASCII digits')
    return tuple(1 if j == int(digit) else 0 for digit in number for j in range(10))


def positional_distance(a: str, b: str) -> int:
    if not is_five_digit_draw(a) or not is_five_digit_draw(b):
        raise ValueError('PL5 numbers must have exactly five ASCII digits')
    return sum(x != y for x, y in zip(a, b))


def _interactions(row: str, cols: tuple[tuple[int, ...], ...]) -> set[tuple]:
    return {(positions, tuple(row[i] for i in positions)) for positions in cols}


def select_diverse_codebook(candidates, *, budget: int,
                            min_distance: int = 3, strength: int = 2) -> list[str]:
    """Deterministic greedy coverage, preserving a HARD distance threshold.

    May return fewer than budget if infeasible. Never claims full coverage or
    optimality. Candidate pool may be an unconstrained CA or another filter.
    """
    if type(budget) is not int or budget < 0 or type(min_distance) is not int or not 1 <= min_distance <= 5:
        raise ValueError('invalid budget or minimum distance')
    if type(strength) is not int or strength not in (2, 3):
        raise ValueError('strength must be 2 or 3')
    available = _validate_numbers(candidates)
    selected: list[str] = []
    seen: set[tuple] = set()
    cols = tuple(combinations(range(5), strength))
    # Deterministic tie-break on the first row from the user-provided pool.
    while len(selected) < budget:
        best_index = None
        best_coverage = -1
        for i, row in enumerate(available):
            if any(positional_distance(row, prior) < min_distance for prior in selected):
                continue
            gain = len(_interactions(row, cols) - seen)
            if gain > best_coverage:
                best_index, best_coverage = i, gain
        if best_index is None:
            break
        row = available.pop(best_index)
        selected.append(row)
        seen.update(_interactions(row, cols))
    return selected


def audit_codebook(numbers, *, strength: int = 2) -> dict:
    rows = _validate_numbers(numbers)
    smallest = min((positional_distance(a, b) for a, b in combinations(rows, 2)), default=None)
    return {
        'schema': 'pl5-v3713-codebook-audit-1',
        'retained_count': len(rows),
        'one_hot_length': 50, 'one_hot_weight': 5,
        'min_positional_distance': smallest,
        'min_binary_one_hot_distance': 2 * smallest if smallest is not None else None,
        'coverage': audit_interactions(rows, strength),
        'fair_draw_exact_hit_probability': len(rows) / 100000,
        'predictive_advantage': 'NOT_ESTABLISHED',
    }
