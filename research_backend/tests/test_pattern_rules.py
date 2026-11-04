import numpy as np
import pytest
from pailie5.pattern_rules import Configuration, filter_next, rolling_backtest, indicator_values, register_indicator
from pailie5.basic_filters import BasicConstraint, apply_basic_filters, combine_basic_and_pattern


def cfg(**kwargs):
    return Configuration(indicators=('digit_5',),transforms=('raw',),patterns=('constant',),windows=(3,),
                         mode='continuation', max_rule_remove=0.65, max_total_remove=0.9,
                         min_keep=1000, **kwargs)


def test_constant_run_bans_continuation():
    result=filter_next(['00002']*3,cfg())
    assert result.summary()['removed']==10000
    assert 2 in result.removed and 12 in result.removed
    assert 3 in result.kept
    assert any(r.status=='applied' and r.banned_values==[2] for r in result.rules)


def test_no_pattern_no_filter():
    result=filter_next(['00001','00002','00003'],cfg())
    assert len(result.kept)==100000


def test_arithmetic_pattern():
    config=Configuration(indicators=('digit_5',),transforms=('raw',),patterns=('arithmetic',),windows=(3,))
    result=filter_next(['00002','00004','00006'],config)
    assert 8 in result.removed and 9 in result.kept
    # 数值越界后不得凭空删除
    result2=filter_next(['00005','00007','00009'],config)
    assert len(result2.kept)==100000


def test_period_2():
    config=Configuration(indicators=('digit_5',),transforms=('raw',),patterns=('period2',),windows=(4,))
    result=filter_next(['00001','00002','00001','00002'],config)
    assert 1 in result.removed and 2 in result.kept


def test_recurrence_only():
    config=Configuration(indicators=('digit_5',),transforms=('raw',),patterns=('constant',),windows=(3,),
                         mode='recurrence',lookback=8)
    result=filter_next(['00001','00001','00001','00002','00002'],config)
    assert 2 in result.removed and 3 in result.kept


def test_default_over_removal_protection():
    history=['00001','00002','00003','00004']*30
    config=Configuration(min_keep=12000,max_total_remove=0.8)
    result=filter_next(history,config)
    assert len(result.kept)>=20000
    assert any(r.status=='skipped' for r in result.rules)


def test_basic_filters_and_intersection():
    constraint=[BasicConstraint('sum',minimum=0,maximum=0)]
    onlyzero=apply_basic_filters(constraint)
    assert onlyzero.tolist()==[0]
    result=filter_next(['00002']*3,cfg())
    combined=combine_basic_and_pattern(constraint,result.kept)
    assert combined.tolist()==[0]


def test_custom_indicators():
    register_indicator('test_head_product',lambda arr: arr[:,0].astype(int)*arr[:,1].astype(int))
    assert indicator_values('test_head_product','raw')[12345]==2
    with pytest.raises(ValueError):
        register_indicator('test_head_product',lambda arr: arr[:,0])


def test_backtest_no_future_leakage():
    nums=[f'{x%10:05d}' for x in range(35)]
    config=cfg()
    earlier=rolling_backtest(nums,config,warmup=20,max_periods=10)
    extended=rolling_backtest(nums+['99999'],config,warmup=20,max_periods=11)
    assert earlier['details']==extended['details'][:-1]
    assert abs(earlier['random_expected_keep']-sum(r['keep_rate'] for r in earlier['details']))<1e-12


def test_validation_rejects_wrong_numbers():
    with pytest.raises(ValueError):
        filter_next(['000001'],cfg())


def test_cross_draw_position_matches():
    config=Configuration(indicators=('same_positions_prev',),transforms=('raw',),
                         patterns=('constant',),windows=(3,))
    result=filter_next(['00000']*4,config)
    assert 0 in result.removed
    assert 1 in result.kept
    assert 10000 in result.kept


def test_cross_draw_sum_delta():
    config=Configuration(indicators=('sum_delta_prev',),transforms=('raw',),
                         patterns=('constant',),windows=(3,))
    result=filter_next(['00001','00003','00005','00007'],config)
    assert 9 in result.removed
    assert 8 in result.kept


def test_backtest_cross_draw_indicators_no_leakage():
    history=[f'{(i*13)%100000:05d}' for i in range(42)]
    config=Configuration(indicators=('digit_overlap_prev','sum_delta_prev'),transforms=('raw',),
                         patterns=('constant','arithmetic'),windows=(3,))
    earlier=rolling_backtest(history,config,warmup=30,max_periods=9)
    later=rolling_backtest(history+['99999'],config,warmup=30,max_periods=10)
    assert earlier['details']==later['details'][:-1]
