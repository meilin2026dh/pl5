"""TDD: exact equivalence and target-leakage guards for opt-in light rolling."""
from dataclasses import replace

import pytest
from pailie5.pattern_rules import Configuration
from pailie5.probability_ranker import rolling_rank_backtest, rank_target_snapshot_v3717
from pailie5.sculpting import rolling_sculpt_backtest
from pailie5.basic_filters import BasicConstraint


def config():
    return Configuration(
        indicators=('digit_5','sum','span','same_positions_prev','sum_delta_prev'),
        transforms=('raw','mod2'),patterns=('constant','strict_up','period2'),
        windows=(3,4),lookback=12,max_rules=25)


def hist(n=75):
    # Synthetic and varied, with leading zeros and temporal context.
    return [f'{(i*i*137+i*31+7)%100000:05d}' for i in range(n)]


@pytest.mark.parametrize('k,strength',[(1000,1.0),(70,0.0),(99999,2.5)])
def test_rank_target_only_exact_report(k,strength):
    history=hist()
    kwargs=dict(config=config(),warmup=40,max_periods=4,top_k=k,strength=strength,
                basic_constraints=[BasicConstraint('sum',minimum=6,maximum=32)])
    old=rolling_rank_backtest(history,**kwargs)
    new=rolling_rank_backtest(history,**kwargs,target_only=True)
    assert new == old


def test_rank_target_only_sorts_complete_universe_before_target_lookup():
    past=hist(50)
    snapshot=rank_target_snapshot_v3717(past,config())
    assert len(snapshot.order)==100_000
    assert snapshot.extract('00000')['rank'] in range(1,100001)
    assert snapshot.extract('99999')['rank'] in range(1,100001)
    assert snapshot.extract('00000')['rank'] != snapshot.extract('99999')['rank']
    with pytest.raises(ValueError):snapshot.extract('１２３４５')
    with pytest.raises(ValueError):snapshot.extract('1234')


def test_rank_target_only_future_draw_leakage_guard():
    h=hist(55)
    before=rolling_rank_backtest(h,config(),warmup=40,max_periods=4,top_k=1000,target_only=True)
    after=rolling_rank_backtest(h+['99999'],config(),warmup=40,max_periods=5,top_k=1000,target_only=True)
    assert before['details']==after['details'][:-1]


@pytest.mark.parametrize('k,strength',[(100,1.0),(333,0.0)])
def test_sculpt_target_only_exact_report(k,strength):
    h=hist(72)
    kwargs=dict(config=config(),warmup=40,max_periods=3,k=k,strength=strength,
                basic=[BasicConstraint('span',minimum=1,maximum=8)])
    old=rolling_sculpt_backtest(h,**kwargs)
    new=rolling_sculpt_backtest(h,**kwargs,target_only=True)
    assert new==old


def test_sculpt_target_only_future_draw_leakage_guard():
    h=hist(70)
    before=rolling_sculpt_backtest(h,config(),warmup=40,max_periods=3,k=100,target_only=True)
    after=rolling_sculpt_backtest(h+['99999'],config(),warmup=40,max_periods=4,k=100,target_only=True)
    assert before['details']==after['details'][:-1]


def test_sculpt_target_only_invalid_or_empty_inputs():
    with pytest.raises(ValueError):
        rolling_sculpt_backtest(['00001']*3,config(),max_periods=1,target_only=True)


def test_context_feature_reuse_produces_identical_full_rule_audit():
    from pailie5.pattern_rules import filter_next
    import numpy as np
    history=hist(130)
    cfg=Configuration(
        indicators=('same_positions_prev','digit_overlap_prev','sum_delta_prev',
                    'span_delta_prev','lastdigit_delta_prev','same_parity_positions_prev',
                    'digit_5','sum'),
        transforms=('raw','mod2','mod3','mod5','mod10'),
        patterns=('constant','strict_up','strict_down','arithmetic','period2','zigzag'),
        windows=(3,4,5),lookback=12,max_rules=80,mode='recurrence')
    before=filter_next(history,cfg)
    after=filter_next(history,cfg,optimize_context=True)
    assert np.array_equal(before.kept, after.kept)
    assert np.array_equal(before.removed, after.removed)
    assert [r.as_dict() for r in before.rules]==[r.as_dict() for r in after.rules]
    assert before.summary()==after.summary()


def test_context_feature_reuse_never_caches_across_different_histories():
    from pailie5.pattern_rules import filter_next
    h=hist(45)
    cfg=config()
    a=filter_next(h,cfg,optimize_context=True)
    b=filter_next(h+['99999'],cfg,optimize_context=True)
    oracle=filter_next(h+['99999'],cfg)
    assert [r.as_dict() for r in b.rules]==[r.as_dict() for r in oracle.rules]
    assert len(a.kept)<=100000 and len(b.kept)<=100000
