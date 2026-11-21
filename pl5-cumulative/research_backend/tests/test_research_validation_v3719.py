"""V3.7.19 auditable protocol + adversarial no-lookahead regressions."""
from __future__ import annotations

import copy
import numpy as np
import pytest

from pailie5.research_validation_v3719 import (
    Draw, Protocol, auxiliary_track_checks, run_walk_forward, synthetic_fair_draws,
    validate_draws,
)


def test_reproducible_predeclared_fair_demo_and_evidence_digests():
    draws = synthetic_fair_draws(n=43, seed=11)
    cfg = Protocol(test_size=3, methods=('random','positional'), top_k=100, seed=88)
    left = run_walk_forward(draws, cfg, input_type='synthetic_fair_iid')
    right = run_walk_forward(draws, cfg, input_type='synthetic_fair_iid')
    assert left == right
    assert left['evidence_level'] == 'RETROSPECTIVE_WALK_FORWARD_ONLY'
    assert left['prospective_precommitment_verified'] is False
    assert left['test_count'] == 3
    assert len(left['predictions']) == 6
    assert left['baseline_per_draw'] == 0.001
    assert all(len(r['candidate_sha256']) == 64 for r in left['predictions'])
    assert left['models'][0]['bonferroni_family_p'] is None
    assert left['models'][1]['bonferroni_family_p'] is not None
    assert all(m['predictive_advantage'] == 'NOT_ESTABLISHED' for m in left['models'])


def test_no_lookahead_candidate_training_unchanged_when_future_changes():
    rows = list(synthetic_fair_draws(n=42, seed=22))
    cfg = Protocol(warmup=40, test_size=2, methods=('random',), seed=2)
    recorded = []

    def frozen_spy(past, method, spec, index):
        recorded.append((index, past))
        assert len(past) == index
        return np.arange(spec.top_k, dtype=np.int32)

    original = run_walk_forward(rows, cfg, input_type='synthetic_fair_iid', predictor=frozen_spy)
    rows[-1] = Draw(rows[-1].issue, '99999')
    modified = run_walk_forward(rows, cfg, input_type='synthetic_fair_iid', predictor=frozen_spy)
    assert recorded[0] == recorded[2]
    assert all(x['candidate_sha256'] == y['candidate_sha256']
               for x,y in zip(original['predictions'],modified['predictions']))
    assert all(x['history_sha256'] == y['history_sha256']
               for x,y in zip(original['predictions'],modified['predictions']))
    assert original['dataset_sha256'] != modified['dataset_sha256']
    # The test algorithm never sees its own period result.
    assert recorded[1][1][-1] == rows[-2].number


def test_all_methods_receive_same_frozen_test_issue():
    rows = synthetic_fair_draws(n=41, seed=15)
    spec = Protocol(test_size=1, methods=('random','positional','pairwise','ensemble','heuristic_rank'))
    out = run_walk_forward(rows, spec, input_type='synthetic_fair_iid')
    p = out['predictions']
    assert len(p) == 5
    assert len({r['issue'] for r in p}) == 1
    assert len({r['history_sha256'] for r in p}) == 1
    assert len({r['candidate_sha256'] for r in p}) == 5


@pytest.mark.parametrize('rows', [
    [], [Draw('2','00001'), Draw('1','12345')],
    [Draw('1','00001'), Draw('01','12345')],
    [Draw('1','00001'), Draw('2','1234')],
    [Draw('1','00001'), Draw('2','１２３４５')],
    [Draw('a','00001')],
])
def test_rejects_bad_input(rows):
    with pytest.raises(ValueError):
        validate_draws(rows)


@pytest.mark.parametrize('changes', [
    {'warmup':29}, {'test_size':0}, {'top_k':100001},
    {'methods':('positional',)}, {'methods':('random','random')},
    {'methods':('random','unknown')}, {'alpha':0}, {'seed':-1},
])
def test_rejects_bad_protocol(changes):
    with pytest.raises(ValueError):
        Protocol(**changes)


def test_cannot_inject_wrong_budget_duplicate_or_bad_ticket():
    rows = synthetic_fair_draws(n=41, seed=3)
    cfg = Protocol(test_size=1, methods=('random',))
    for output in (np.arange(99), np.zeros(100, dtype=int),
                   np.arange(100)+100000, np.arange(100, dtype=float)):
        with pytest.raises(ValueError):
            run_walk_forward(rows, cfg, input_type='synthetic_fair_iid',
                             predictor=lambda *args, x=output: x)


def test_track_adapters_use_separate_metrics_and_no_label_fit():
    tracks = auxiliary_track_checks(seed=8)
    assert tracks == auxiliary_track_checks(seed=8)
    assert tracks['nca']['holdout'] == 30
    assert tracks['math_language']['holdout_cells'] > 0
    assert tracks['math_language']['holdout_errors'] == 0
    assert tracks['ga_cs']['evaluation_budget_each'] == 48
    assert tracks['ga_cs']['lottery_draw_labels_used'] is False
    assert tracks['production_enabled'] is False
    assert tracks['predictive_advantage'] == 'NOT_ESTABLISHED'


def test_no_confirmation_of_prediction_just_by_random_hit():
    # Deliberately force a target hit: still cannot claim independent prediction.
    rows = list(synthetic_fair_draws(n=41, seed=3))
    rows[-1] = Draw(rows[-1].issue,'00000')
    result = run_walk_forward(rows, Protocol(test_size=1, methods=('random',)),
                              input_type='synthetic_fair_iid',
                              predictor=lambda h,m,p,i:np.arange(p.top_k, dtype=int))
    assert result['models'][0]['hits'] == 1
    assert result['predictive_advantage'] == 'NOT_ESTABLISHED'
