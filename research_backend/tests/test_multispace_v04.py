"""V0.4 集成、安全、数学基线、竞争和稳健性回归测试。"""
import numpy as np
import pandas as pd
import pytest
from math import gcd

from pailie5.multispace import (
    multi_space_study, select_indicators, space_of_indicator,
    _competition,
)
from pailie5.mapping_robustness import (
    fixed_variants, variant_arrays, variant_features, robustness_study,
)
from pailie5.space_mapping import SPACES, mapping_array
from pailie5.pattern_rules import Rule


HISTORY=[f'{(i*2999+i*i*13)%100000:05d}' for i in range(80)]
INDICATORS={
  'pl5':('sum','span'),
  'pick23_6':('sum','span'),
  'pick41_4':('sum','consecutive_pairs'),
  'ternary11':('three_count','switch_count'),
}


def test_multispace_register_and_validate():
    result=select_indicators(INDICATORS)
    assert len(result)==8
    assert 'pick23_6__sum' in result
    assert space_of_indicator('sum')=='pl5'
    assert space_of_indicator('ternary11__three_count')=='ternary11'
    with pytest.raises(ValueError): select_indicators({'fake':('sum',)})
    with pytest.raises(ValueError): select_indicators({'pick23_6':('three_count',)})
    with pytest.raises(ValueError): select_indicators({})


def test_multispace_full_100k_rank_and_probability_guard():
    a=multi_space_study(HISTORY,INDICATORS,patterns=('constant','strict_up','arithmetic'),
                        transforms=('raw',),windows=(3,4))
    assert len(a.table)==100000
    assert a.table.number.nunique()==100000
    assert a.table['rank'].iloc[-1]==100000
    assert abs(a.table['model_weight'].sum()-1)<1e-10
    assert set(a.table['fair_probability'])=={1e-5}
    assert len(a.history_table)==len(HISTORY)
    assert set(a.metadata['spaces'])==set(INDICATORS)
    assert a.competition['total_union_removed']<=100000
    assert '未校准' in a.metadata['note']
    with pytest.raises(ValueError): a.top(0)


def test_competition_union_increment_and_pair_overlap():
    a=np.zeros(100000,dtype=bool); a[:10000]=True
    b=np.zeros(100000,dtype=bool); b[5000:15000]=True
    r1=Rule('sum','raw','constant',3,'continuation',[1,1,1],[1],10000,.1)
    r2=Rule('pick23_6__sum','raw','constant',3,'continuation',[1,1,1],[1],10000,.1)
    rows,result=_competition([r1,r2],[a,b],20)
    assert [r['marginal_exclusions'] for r in rows]==[10000,5000]
    assert result['total_union_removed']==15000
    pair=result['space_overlap'][0]
    assert abs(pair['jaccard']-1/3)<1e-10
    assert abs(pair['phi_correlation']-(.05-.1*.1)/.09)<1e-10


def test_allow_explicit_zero_rules_reverts_fair():
    a=multi_space_study(HISTORY,{'pl5':('sum',)},selected_rule_keys=[])
    assert a.metadata['accepted_rules']==0
    assert np.allclose(a.table['model_weight'],1e-5)
    assert (a.table['number'].iloc[:3]==pd.Series(['00000','00001','00002'])).all()
    with pytest.raises(ValueError):
        multi_space_study(HISTORY,{'pl5':('sum',)},selected_rule_keys=['bogus'])


@pytest.mark.parametrize('space',list(SPACES))
def test_fixed_variant_params_reproducible_and_injective(space):
    a=fixed_variants(space,4)
    b=fixed_variants(space,4)
    assert a==b
    assert a[0]['multiplier']==SPACES[space].multiplier
    assert a[0]['offset']==SPACES[space].offset
    for var in a:
        arr=variant_arrays(space,var['multiplier'],var['offset'])
        assert arr.shape==(100000,SPACES[space].positions)
        assert gcd(var['multiplier'],SPACES[space].size)==1
        # 代数证明单射，同时抽检数据和官方映射的一致性
        ranks=(var['multiplier']*np.arange(100000)+var['offset'])%SPACES[space].size
        assert len(np.unique(ranks))==100000
    assert np.array_equal(variant_arrays(space,a[0]['multiplier'],a[0]['offset']),
                          mapping_array(space))


def test_robustness_same_holdout_and_no_future_leak():
    history=HISTORY[:62]
    kw={'space':'pick23_6','metrics':('sum','span'),'variant_count':3,
        'warmup':35,'holdout':12,'top_k':1000}
    a=robustness_study(history,**kw)
    b=robustness_study(history+['99999'],**{**kw,'holdout':13})
    assert len(a['details'])==36
    for variant in a['variants']:
        assert variant['periods']==12
        assert variant['fair_expected_hits']==pytest.approx(.12)
    # 对于相同的被测期，增加未来开奖不能改变其预测位置。
    assert [row for row in b['details'] if row['index']<62] == a['details']
    assert len(a['current_set_overlap'])==2
    assert all(x['jaccard_with_canonical'] is None or 0<=x['jaccard_with_canonical']<=1 for x in a['current_set_overlap'])
    assert a['canonical']==a['variants'][0]


def test_metrics_validation_and_variants_seed():
    assert fixed_variants('pick23_6',3,'seed-A')!=fixed_variants('pick23_6',3,'seed-B')
    with pytest.raises(ValueError):
        robustness_study(HISTORY,'pick23_6',('three_count',))
    with pytest.raises(ValueError):
        robustness_study(HISTORY,'pick23_6',('sum',),warmup=1000)
    with pytest.raises(ValueError):
        fixed_variants('pick23_6',1)


def test_robustness_deterministic():
    a=robustness_study(HISTORY,'ternary11',('three_count',),variant_count=2,
                       warmup=40,holdout=4)
    b=robustness_study(HISTORY,'ternary11',('three_count',),variant_count=2,
                       warmup=40,holdout=4)
    assert a==b


def test_competition_backtest_same_past_windows():
    from pailie5.multispace import competition_backtest
    config={'pl5':('sum',),'pick23_6':('span',)}
    a=competition_backtest(HISTORY[:61],config,warmup=40,max_periods=8)
    b=competition_backtest(HISTORY[:61]+['00000'],config,warmup=40,max_periods=9)
    assert a['details']==b['details'][:-1]
    assert a['per_space'][0]['periods']==8
    assert all(0<=v['random_expected_exclusion_rate']<=1 for v in a['per_space'])
    assert all(0<=v['random_expected_exclusion_rate_if_triggered']<=1 for v in a['per_rule'])
