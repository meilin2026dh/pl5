"""The preregistered challenge separates study generation and frozen evaluation."""
import pytest
import numpy as np
from pailie5.adaptive_study_v379 import protocol, challenge_truth, run_predeclared


def test_study_protocol_reproducible_and_locks_choices():
    a = protocol((9201, 9202))
    assert a == protocol((9201, 9202))
    assert a['holdout_count'] == 30 and a['train_count'] == 70
    output = run_predeclared(a)
    assert output == run_predeclared(a)
    assert len(output['trials']) == len(a['cases'])*2
    assert all(x['model']['production_enabled'] is False for x in output['trials'])


def test_modified_protocol_cannot_run():
    cfg=protocol((9201,))
    cfg['holdout_count']=20
    with pytest.raises(ValueError, match='preregistration'):
        run_predeclared(cfg)


def test_truth_seeds_generate_different_math_tables():
    for case in ['rank_a2b','split_sum','iid_random']:
        x=challenge_truth(case, 9201)
        y=challenge_truth(case, 9202)
        assert x.shape == (10,10) and x.dtype == np.uint8
        assert not np.array_equal(x,y)


def test_all_trials_are_stored_without_holdout_guided_fitting():
    results=run_predeclared(protocol((9211,)))
    for r in results['trials']:
        assert r['train_pairs']==70 and r['held_pairs']==30
        assert r['train_sha256'] != r['holdout_sha256']
        assert r['frozen_without_holdout'] is True
        assert r['production_enabled'] is False
