import numpy as np
import pytest
from pailie5.pattern_rules import Configuration, filter_next
from pailie5.probability_ranker import (
    FAIR_PROBABILITY, rank_all_numbers, rolling_rank_backtest, rule_key
)
from pailie5.basic_filters import BasicConstraint


def cfg(**kwargs):
    return Configuration(indicators=('digit_5',),transforms=('raw',),
       patterns=('constant',),windows=(3,),mode='continuation',
       max_rule_remove=0.65,max_total_remove=0.9,min_keep=1000, **kwargs)


def test_rank_probabilities_are_normalized_and_ordered():
    output=rank_all_numbers(['00002']*3,cfg())
    df=output.table
    assert len(df)==100_000
    assert df['number'].nunique()==100_000
    assert abs(df['model_probability'].sum()-1.0)<1e-12
    assert abs(df['fair_probability'].sum()-1.0)<1e-12
    assert df['model_probability'].is_monotonic_decreasing
    p2=float(df.loc[df.number=='00002','model_probability'].iloc[0])
    p3=float(df.loc[df.number=='00003','model_probability'].iloc[0])
    assert p2 < p3
    assert int(df.loc[df.number=='00002','hit_rules'].iloc[0])==1
    assert output.summary(top_k=1000)['fair_top_k_coverage']==0.01


def test_no_signals_returns_uniform_baseline():
    out=rank_all_numbers(['00001','00002','00003'],cfg())
    assert out.metadata['zero_signal']
    assert np.allclose(out.table['model_probability'],FAIR_PROBABILITY)


def test_zero_strength_is_exact_fair_baseline():
    out=rank_all_numbers(['00002']*3,cfg(),strength=0)
    assert out.metadata['zero_signal']
    assert np.allclose(out.table['model_probability'],FAIR_PROBABILITY)


def test_manual_rule_selection_and_validation():
    history=['00002']*3
    actual_rule=filter_next(history,cfg()).rules[0]
    out=rank_all_numbers(history,cfg(),selected_rule_keys=[])
    assert out.metadata['selected_rule_count']==0
    selected=rank_all_numbers(history,cfg(),selected_rule_keys=[rule_key(actual_rule)])
    assert selected.metadata['selected_rule_count']==1
    with pytest.raises(ValueError):
        rank_all_numbers(history,cfg(),selected_rule_keys=['madeup'])


def test_basic_constraint_is_display_only():
    out=rank_all_numbers(['00002']*3,cfg(),basic_constraints=[BasicConstraint('sum',minimum=0,maximum=0)])
    assert out.table['basic_pass'].sum()==1
    assert abs(out.table['model_probability'].sum()-1)<1e-12


def test_rank_backtest_uses_only_past():
    history=[f'{n%10:05d}' for n in range(34)]
    prior=rolling_rank_backtest(history,cfg(),warmup=30,max_periods=4,top_k=1000)
    later=rolling_rank_backtest(history+['99999'],cfg(),warmup=30,max_periods=5,top_k=1000)
    assert prior['details']==later['details'][:-1]


def test_rank_rejects_bad_strength():
    with pytest.raises(ValueError):
        rank_all_numbers(['00002']*3,cfg(),strength=-0.1)
