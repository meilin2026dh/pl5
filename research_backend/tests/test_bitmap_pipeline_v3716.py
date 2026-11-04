"""TDD for opt-in exact bitset integration with actual PL5 scientific workflows."""
import numpy as np
import pytest

from pailie5.basic_filters import BasicConstraint, apply_basic_filters, combine_basic_and_pattern
from pailie5.basic_filter_catalog_v3716 import BasicFilterCatalog
from pailie5.pattern_rules import Configuration, filter_next
from pailie5.probability_ranker import rank_all_numbers, rolling_rank_backtest
from pailie5.sculpting import knives_from_history, rolling_sculpt_backtest


RULES = [
    BasicConstraint('sum', minimum=7, maximum=32),
    BasicConstraint('span', minimum=2, maximum=9),
    BasicConstraint('odd_count', minimum=1, maximum=4),
    BasicConstraint('digit_1', denied=(9,)),
    BasicConstraint('digit_5', allowed=(0,1,2,3,4,5,6,7,8)),
]


def history():
    return [f'{((i * 8719) + (i % 4) * 101) % 100000:05d}' for i in range(46)]


def config():
    return Configuration(indicators=('sum','span','odd_count','digit_5','same_positions_prev'),
                         transforms=('raw',),patterns=('constant','strict_up','period2'),
                         windows=(3,4),lookback=10,max_rules=25,min_keep=2500)


def test_catalog_full_and_subsets_match_legacy_oracle():
    catalog=BasicFilterCatalog(RULES)
    assert catalog.select(RULES).tolist()==apply_basic_filters(RULES).tolist()
    assert catalog.select([]).size == 100000
    assert catalog.select([RULES[2]]).tolist()==apply_basic_filters([RULES[2]]).tolist()
    assert catalog.select([RULES[2],RULES[2]]).tolist()==apply_basic_filters([RULES[2]]).tolist()
    assert catalog.stats()['cached_rules']==5
    assert catalog.stats()['compilations']==5


def test_catalog_cannot_silently_accept_different_parameters():
    catalog=BasicFilterCatalog(RULES)
    with pytest.raises(ValueError,match='not registered'):
        catalog.select([BasicConstraint('sum',minimum=2,maximum=15)])
    with pytest.raises(ValueError,match='duplicate'):
        BasicFilterCatalog([RULES[0],RULES[0]])


def test_catalog_refresh_rebuilds_dependency_cache():
    catalog=BasicFilterCatalog(RULES)
    catalog.select(RULES)
    assert catalog.refresh('indicator:sum')==1
    catalog.select(RULES)
    assert catalog.stats()['compilations']==6


def test_basic_pattern_intersection_is_identical():
    pattern=filter_next(history(),config()).kept
    catalog=BasicFilterCatalog(RULES)
    a=combine_basic_and_pattern(RULES,pattern)
    b=combine_basic_and_pattern(RULES,pattern,basic_catalog=catalog)
    assert np.array_equal(a,b)
    assert np.array_equal(a,np.intersect1d(apply_basic_filters(RULES),pattern,assume_unique=True))


def test_rank_pipeline_and_full_walkforward_are_exact():
    hist=history()
    cfg=config()
    catalog=BasicFilterCatalog(RULES)
    before=rank_all_numbers(hist,cfg,basic_constraints=RULES)
    after=rank_all_numbers(hist,cfg,basic_constraints=RULES,basic_catalog=catalog)
    assert before.table.equals(after.table)
    assert before.metadata==after.metadata
    assert before.rule_details==after.rule_details
    a=rolling_rank_backtest(hist,cfg,warmup=35,max_periods=2,top_k=100,
                            basic_constraints=RULES)
    b=rolling_rank_backtest(hist,cfg,warmup=35,max_periods=2,top_k=100,
                            basic_constraints=RULES,basic_catalog=catalog)
    assert a==b


def test_sculpt_pipeline_and_full_walkforward_are_exact():
    hist=history()
    cfg=config()
    catalog=BasicFilterCatalog(RULES)
    before,selected1=knives_from_history(hist,cfg,basic=RULES)
    after,selected2=knives_from_history(hist,cfg,basic=RULES,basic_catalog=catalog)
    assert selected1==selected2
    assert len(before)==len(after)
    for a,b in zip(before,after):
        assert a.key==b.key
        assert np.array_equal(a.excluded,b.excluded)
    a=rolling_sculpt_backtest(hist,cfg,k=20,warmup=35,max_periods=2,basic=RULES)
    b=rolling_sculpt_backtest(hist,cfg,k=20,warmup=35,max_periods=2,basic=RULES,basic_catalog=catalog)
    assert a==b


def test_empty_and_leading_zero_cases():
    catalog=BasicFilterCatalog([BasicConstraint('sum',maximum=0)])
    assert catalog.select([BasicConstraint('sum',maximum=0)]).tolist()==[0]
    assert catalog.formatted([BasicConstraint('sum',maximum=0)])==['00000']
