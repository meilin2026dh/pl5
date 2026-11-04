"""Acceptance tests written before V3.7.8 study implementation."""
import pytest
from pailie5.coupled_study_v378 import preregister, run_registered, challenge_truth


def test_protocol_is_locked_and_runs_multiple_targets():
    settings = preregister(seeds=(101, 102, 103))
    outcome = run_registered(settings)
    assert outcome['protocol_sha256']
    assert outcome['summary']['trials'] == 24
    assert all(x['test_pairs'] == 30 for x in outcome['trials'])
    assert all(x['production_enabled'] is False for x in outcome['trials'])


def test_modified_protocol_rejected():
    settings = preregister(seeds=(101,))
    settings['train_pairs'] = 99
    with pytest.raises(ValueError):
        run_registered(settings)


def test_deterministic_replay():
    x = preregister(seeds=(111,))
    assert run_registered(x) == run_registered(x)


def test_negative_target_does_not_duplicate_positive_structure():
    x = challenge_truth('piecewise_absolute', 123)
    y = challenge_truth('rank_one_quadratic', 123)
    assert x.shape == (10, 10) and y.shape == (10, 10)
    assert not (x == y).all()


def test_rejects_unknown_case_and_bad_seed():
    with pytest.raises(ValueError):
        challenge_truth('lottery', 17)
    with pytest.raises(ValueError):
        preregister(seeds=(True,))
