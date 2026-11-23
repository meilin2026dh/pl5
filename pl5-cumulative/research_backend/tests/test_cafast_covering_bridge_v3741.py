"""Cross-check V3.7.41 algebraic and deletion construction, without label data."""
from collections import Counter
from itertools import combinations, product

import pytest

from pailie5.covering_arrays_v3713 import audit_interactions
from pailie5.cafast_covering_bridge_v3741 import (
    algebraic_start, experiment, prune_once, verify_counts,
)


@pytest.mark.parametrize("strength,initial", [(2, 120), (3, 1330), (4, 14361)])
def test_initial_algebraic_t_cover_and_exact_tuple_count(strength, initial):
    rows = algebraic_start(strength)
    assert len(rows) == initial
    output = verify_counts(rows, strength)
    assert output["full_coverage"]
    assert output["missing_tuples"] == 0
    assert output["required_tuples"] == len(tuple(combinations(range(5), strength))) * 10**strength
    assert audit_interactions(rows, strength)["missing"] == 0


@pytest.mark.parametrize("strength,expected_upper", [(2, 119), (3, 1288), (4, 12367)])
def test_multistart_32_frozen_seeds_reproduces_verified_upper_bounds(strength, expected_upper):
    output, audit = experiment(strength, seeds=tuple(range(32)))
    assert len(output) <= expected_upper
    assert len(output) == audit["best_rows"]
    assert audit["missing_tuples"] == 0
    assert audit["thin_tuples"] > 0
    assert audit["simple_theoretical_lower_bound"] == 10**strength
    assert len(audit["trials"]) == 32
    assert audit["construction_is_proven_minimum"] is False
    assert audit["historical_data_read"] is False


def test_randomized_deletion_never_destroys_coverage_and_is_deterministic():
    rows = algebraic_start(3)
    a = prune_once(rows, 3, 5)
    b = prune_once(rows, 3, 5)
    assert a == b
    assert len(a) < len(rows)
    assert set(a).issubset(rows)
    assert verify_counts(a, 3)["missing_tuples"] == 0


def test_independent_plain_python_tuple_count_oracle():
    rows, audit = experiment(2, seeds=(0, 1))
    combos = tuple(combinations(range(5), 2))
    witnessed = {(c, tuple(row[i] for i in c))
                 for row in rows for c in combos}
    expected = {(c, pair) for c in combos for pair in product("0123456789", repeat=2)}
    assert witnessed == expected
    assert audit["required_tuples"] == len(expected)


@pytest.mark.parametrize("bad", ["1234", "１２３４５", "ABCDE"])
def test_bad_digit_rows_fail_closed(bad):
    with pytest.raises(ValueError):
        verify_counts([bad], 2)


def test_duplicate_and_missing_tuple_inputs_rejected():
    with pytest.raises(ValueError):
        verify_counts(["00000", "00000"], 2)
    with pytest.raises(ValueError):
        prune_once(["00000"], 2, seed=1)


@pytest.mark.parametrize("invalid", [0, 1, 5, True])
def test_invalid_strength_fails_closed(invalid):
    with pytest.raises(ValueError):
        algebraic_start(invalid)


def test_invalid_seeds_and_negative_pruning_seed_rejected():
    with pytest.raises(ValueError):
        experiment(2, seeds=(1, 1))
    with pytest.raises(ValueError):
        experiment(2, seeds=())
    with pytest.raises(ValueError):
        prune_once(algebraic_start(2), 2, -1)
