"""V3.7.13 PL5 digit interaction covering arrays (research test design only).

Algebraic GF(11) construction: polynomial evaluations at five distinct field
points give strength-t orthogonal arrays over eleven levels. Coarsening the
field element 10 to digit 9 preserves t-way *surjective* coverage over ten
levels; it does NOT prove optimal row count or fair digit frequencies.
"""
from __future__ import annotations

from itertools import combinations, product
from .number_validation import is_five_digit_draw


def _validate_numbers(numbers) -> list[str]:
    if isinstance(numbers, (str, bytes)):
        raise ValueError('expected collection of PL5 identifiers, not one string')
    values = list(numbers)
    if any(not is_five_digit_draw(n) for n in values):
        raise ValueError('PL5 numbers must be five ASCII digits [0-9]{5}')
    if len(set(values)) != len(values):
        raise ValueError('duplicate PL5 number in codebook')
    return values


def generate_pl5_covering_array(strength: int = 2) -> list[str]:
    """Deterministically construct a verified CA for t in {2,3}; not smallest."""
    if type(strength) is not int or strength not in (2, 3):
        raise ValueError('only strength 2 or 3 algebraic designs are supported')
    rows: list[str] = []
    seen: set[str] = set()
    for coefficients in product(range(11), repeat=strength):
        cells = []
        for x in range(5):
            digit = sum(c * pow(x, degree, 11) for degree, c in enumerate(coefficients)) % 11
            cells.append(str(min(digit, 9)))
        codeword = ''.join(cells)
        if codeword not in seen:
            rows.append(codeword)
            seen.add(codeword)
    return rows


def interaction_set(numbers, strength: int = 2) -> set[tuple[tuple[int, ...], tuple[str, ...]]]:
    if type(strength) is not int or strength not in (1, 2, 3, 4, 5):
        raise ValueError('strength must be in 1..5')
    rows = _validate_numbers(numbers)
    return {(cols, tuple(row[j] for j in cols))
            for row in rows for cols in combinations(range(5), strength)}


def audit_interactions(numbers, strength: int = 2) -> dict:
    """Independently enumerate realized interactions, not predicted results."""
    covered = len(interaction_set(numbers, strength))
    total = len(tuple(combinations(range(5), strength))) * 10 ** strength
    return {
        'schema': 'pl5-v3713-covering-audit-1', 'strength': strength,
        'covered': covered, 'required': total, 'missing': total - covered,
        'coverage_fraction': covered / total, 'is_proven_minimum': False,
        'target_type': 'digit_interaction_not_lottery_prediction',
        'predictive_advantage': 'NOT_ESTABLISHED',
    }
