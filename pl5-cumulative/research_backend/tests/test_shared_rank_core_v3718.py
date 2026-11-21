"""V3.7.18: TDD tests for one ranking semantics across both public adapters."""
import numpy as np
import pytest

from pailie5.basic_filters import BasicConstraint
from pailie5.pattern_rules import Configuration, filter_next
from pailie5 import probability_ranker as ranker


def _config():
    return Configuration(
        indicators=('digit_5', 'sum', 'span', 'same_positions_prev', 'sum_delta_prev'),
        transforms=('raw', 'mod2'),
        patterns=('constant', 'strict_up', 'period2'),
        windows=(3, 4), lookback=12, max_rules=25,
    )


def _history(n=53):
    return [f'{(i*i*137 + i*31 + 7) % 100000:05d}' for i in range(n)]


def test_full_and_snapshot_use_the_same_rank_core(monkeypatch):
    """Force both public APIs to delegate to a single function, not two implementations."""
    scorer = ranker._rank_core_v3718
    calls = []

    def traced(*args, **kwargs):
        calls.append(kwargs.get('optimize_context'))
        return scorer(*args, **kwargs)

    monkeypatch.setattr(ranker, '_rank_core_v3718', traced)
    history = _history()
    full = ranker.rank_all_numbers(history, _config())
    thin = ranker.rank_target_snapshot_v3717(history, _config())
    assert len(calls) == 2
    assert np.array_equal(thin.order, full.table.number.map(int).to_numpy())


@pytest.mark.parametrize('strength', [0.0, 1.0, 3.2])
def test_snapshot_matches_full_for_all_target_digits(strength):
    history = _history()
    cfg = _config()
    rules = [BasicConstraint('sum', minimum=5, maximum=35)]
    full = ranker.rank_all_numbers(history, cfg, strength=strength, basic_constraints=rules)
    snapshot = ranker.rank_target_snapshot_v3717(history, cfg, strength=strength, basic_constraints=rules)
    assert snapshot.selected_rule_count == full.metadata['selected_rule_count']
    assert np.array_equal(snapshot.order, full.table.number.map(int).to_numpy())
    for target in ('00000', '99999', history[-1], '01234', '55555'):
        row = full.table.loc[full.table.number.eq(target)].iloc[0]
        extracted = snapshot.extract(target)
        assert extracted['rank'] == int(row['rank'])
        assert extracted['model_probability'] == float(row['model_probability'])


def test_manual_selection_and_invalid_keys_consistent():
    history = ['00002'] * 4
    cfg = Configuration(indicators=('digit_5',), transforms=('raw',),
                        patterns=('constant',), windows=(3,), mode='continuation')
    keys = [ranker.rule_key(r) for r in filter_next(history, cfg).rules]
    for selected in ([], keys):
        full = ranker.rank_all_numbers(history, cfg, selected_rule_keys=selected)
        thin = ranker.rank_target_snapshot_v3717(history, cfg, selected_rule_keys=selected)
        assert thin.selected_rule_count == full.metadata['selected_rule_count']
        assert np.array_equal(thin.order, full.table.number.map(int).to_numpy())
    with pytest.raises(ValueError):
        ranker.rank_target_snapshot_v3717(history, cfg, selected_rule_keys=['not-a-rule'])
    with pytest.raises(ValueError):
        ranker.rank_all_numbers(history, cfg, selected_rule_keys=['not-a-rule'])


def test_target_snapshot_does_not_build_full_dataframe(monkeypatch):
    history = _history()
    def fail(*args, **kwargs):
        raise AssertionError('target-only path should never allocate a full ranking DataFrame')
    monkeypatch.setattr(ranker.pd, 'DataFrame', fail)
    snapshot = ranker.rank_target_snapshot_v3717(history, _config())
    assert 1 <= snapshot.extract('00000')['rank'] <= 100000
