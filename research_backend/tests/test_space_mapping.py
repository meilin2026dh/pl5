"""跨空间映射审计测试：数字覆盖、正反可逆、编码没有非法复用、回测不泄漏。"""
import numpy as np
import pytest
from math import comb

from pailie5.space_mapping import (
    SPACES, mapping_array, mapping_coverage, encoding_of, inverse_encoding,
    mapped_rank, inverse_rank, register_space_indicators, _combinadic_rank,
)
from pailie5.pattern_rules import Configuration, indicator_values, historical_indicators, rolling_backtest
from pailie5.probability_ranker import rank_all_numbers


def test_actual_space_sizes():
    assert comb(23,6)==100947
    assert comb(41,4)==101270
    assert comb(30,7)==2035800
    assert 3**11==177147

@pytest.mark.parametrize('space',list(SPACES))
def test_all_100k_are_one_to_one_and_rank_reversible(space):
    sp=SPACES[space]
    ranks=(sp.multiplier*np.arange(100_000,dtype=np.int64)+sp.offset)%sp.size
    assert len(np.unique(ranks))==100_000
    assert ranks.min()>=0 and ranks.max()<sp.size
    assert all(inverse_rank(int(mapped_rank(i,space)),space)==f'{i:05d}' for i in [0,1,23,128,9999,10000,99999])
    assert mapping_coverage(space)['unmapped']==sp.size-100000

@pytest.mark.parametrize('space',list(SPACES))
def test_roundtrip_readable_encoding(space):
    for x in ['00000','00128','03104','31791','99999']:
        assert inverse_encoding(encoding_of(x,space),space)==x

@pytest.mark.parametrize('space',list(SPACES))
def test_array_legality_and_unassigned_space_code(space):
    a=mapping_array(space)
    assert a.shape==(100_000,SPACES[space].positions)
    if SPACES[space].kind=='combination':
        assert np.all(np.diff(a,axis=1)>0)
        assert a.min()>=1 and a.max()<=SPACES[space].alphabet
        for n in [0,123,99999]:
            assert _combinadic_rank(tuple(int(x)-1 for x in a[n]),SPACES[space].alphabet,SPACES[space].positions)==mapped_rank(n,space)
    else:
        assert a.min()==0 and a.max()==2
    # Exactly size-100000 target states must stay unused.
    for r in range(SPACES[space].size):
        if inverse_rank(r,space) is None:
            break
    else:
        pytest.fail('没有预期的未分配目标状态')


def test_register_indicators_compatible_with_pattern_and_ranking():
    names=register_space_indicators()
    assert len(names)>=30
    assert 'pick23_6__sum' in names
    assert 'ternary11__same_positions_prev' in names
    assert indicator_values('pick23_6__sum','raw').shape==(100_000,)
    history=['00101','00234','30125','12345','12346','99999']*8
    recent=historical_indicators(history, ('pick23_6__sum','ternary11__same_positions_prev'))
    assert len(recent)==len(history)
    assert recent[0]['ternary11__same_positions_prev'] is None
    cfg=Configuration(indicators=('pick23_6__sum','ternary11__same_positions_prev'),
                      patterns=('constant','arithmetic'),windows=(3,),transforms=('raw',))
    out=rank_all_numbers(history,cfg)
    assert len(out.table)==100000
    assert out.table['number'].nunique()==100000
    assert abs(out.table['model_probability'].sum()-1)<1e-10


def test_forward_backtest_no_future_leak():
    register_space_indicators()
    history=[f'{(i*871+35)%100000:05d}' for i in range(42)]
    cfg=Configuration(indicators=('pick23_6__sum',),
                      patterns=('constant','strict_up','strict_down'),windows=(3,),transforms=('raw',))
    a=rolling_backtest(history,cfg,warmup=30,max_periods=12)
    b=rolling_backtest(history+['99999'],cfg,warmup=30,max_periods=13)
    assert a['details']==b['details'][:-1]


def test_reject_invalid_mapping():
    with pytest.raises(ValueError):
        encoding_of('1234','pick23_6')
    with pytest.raises(ValueError):
        inverse_encoding('1 1 2 3 4 5','pick23_6')
    with pytest.raises(ValueError):
        inverse_encoding('11111','ternary11')
