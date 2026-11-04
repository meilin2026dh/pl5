"""V1.1 ESSE regression and mathematical invariants."""
import numpy as np
import pytest

from pailie5.sculpting import Knife, SculptSession, knives_from_history, rolling_sculpt_backtest
from pailie5.pattern_rules import Configuration
from pailie5.basic_filters import BasicConstraint


def knife(key, begin, end, group='g', weight=1.):
    mask=np.zeros(100_000,dtype=bool)
    mask[begin:end]=True
    return Knife(key,key,mask,group=group,weight=weight)


def test_overlap_unique_and_counterfactual():
    s=SculptSession([knife('a',0,200),knife('b',100,300)])
    result=s.sculpt()
    assert result.audit['removed']==300
    assert [(x.newly_removed,x.already_removed,x.unique_recoverable) for x in result.stages]==[(200,0,100),(100,100,100)]
    assert [x['recoverable_if_disabled'] for x in s.counterfactual()]==[100,100]


def test_undo_redo_including_protected_leading_zeros():
    s=SculptSession([knife('a',0,200),knife('b',100,300)])
    s.set_enabled('a',False)
    assert s.sculpt().audit['removed']==200
    s.protect('00128')
    assert s.sculpt().audit['removed']==199
    assert s.undo() is True
    assert s.sculpt().audit['removed']==200
    assert s.undo() is True
    assert s.sculpt().audit['removed']==300
    assert s.redo() is True
    assert s.sculpt().audit['removed']==200
    assert s.redo() is True
    assert s.sculpt().audit['removed']==199
    assert not s.redo()


def test_unverified_label_does_not_bypass_strict_gate():
    x=knife('a',0,200)
    x=Knife(x.key,x.label,x.excluded,evidence='independently_verified')
    s=SculptSession([x],mode='strict')
    assert s.sculpt().audit['removed']==0
    assert s.sculpt().audit['unapproved_blocked']==1
    s2=SculptSession([x],mode='strict',approved_keys={'a'})
    assert s2.sculpt().audit['removed']==200


def test_order_unchanged_final_intersection_and_reversible():
    s=SculptSession([knife('a',0,200),knife('b',100,300)])
    old=s.sculpt().kept_mask.copy()
    s.move('b',-1)
    new=s.sculpt()
    assert np.array_equal(old,new.kept_mask)
    assert [x.newly_removed for x in new.stages]==[200,100]
    assert [x.key for x in new.stages]==['b','a']
    assert s.undo()
    assert s.order == ('a','b')


def test_quota_repair_selects_exactly_k_and_flags_restorations():
    s=SculptSession([knife('a',0,99_950)])
    table, report=s.rank(k=100)
    assert len(table)==100_000
    assert int(table['selected_top_k'].sum())==100
    assert report['restored_for_quota']==50
    assert int(table.head(100)['hard_kept'].sum())==50
    assert int(table.head(100)['restored_for_quota'].sum())==50
    assert report['fair_top_k_coverage']==.001
    assert not report['preference_weight_is_predictive_probability']
    assert np.isclose(table['preference_weight_uncalibrated'].sum(),1)
    assert np.allclose(table['fair_probability'],1e-5)


def test_priority_kept_before_banned_even_if_penalty_low():
    s=SculptSession([knife('a',0,90_000,weight=0)])
    table,_=s.rank(k=100)
    assert all(table.head(100)['hard_kept'])
    assert all(table.head(100)['number'].astype(int).ge(90_000))


def test_inactive_rule_not_affecting_scores():
    s=SculptSession([knife('a',0,100),knife('b',500,800)])
    s.set_enabled('b',False)
    result=s.sculpt()
    assert result.audit['removed']==100
    assert np.all(result.penalty[500:800] == 0)


def test_groupwise_max_prevents_double_penalty():
    k=knife('a',0,400,group='same')
    x=SculptSession([k]).sculpt().penalty
    y=SculptSession([k,knife('b',0,400,group='same')]).sculpt().penalty
    assert np.array_equal(x,y)


def test_greedy_order_determinism_and_undo():
    s=SculptSession([knife('tiny',0,10),knife('big',100,300),knife('mid',50,110)])
    order=s.suggest_greedy_order()
    assert order[0]=='big'
    assert set(order)==set(s.order)
    s.set_order(order)
    assert s.undo()
    assert s.order==('tiny','big','mid')


def test_refuse_malformed_misleading_inputs():
    with pytest.raises(ValueError): Knife('a','bad',np.ones(10,dtype=bool))
    with pytest.raises(ValueError): Knife('a','bad',np.ones(100_000,dtype=int))
    with pytest.raises(ValueError): SculptSession([knife('a',0,1),knife('a',2,3)])
    with pytest.raises(ValueError): SculptSession([knife('a',0,1)],enabled=['b'])
    with pytest.raises(ValueError): SculptSession([knife('a',0,1)],mode='strict',approved_keys=['bad'])
    s=SculptSession([knife('a',0,1)])
    with pytest.raises(ValueError): s.protect('1234')
    with pytest.raises(ValueError): s.rank(k=0)
    with pytest.raises(ValueError): s.set_order(['a','a'])


def test_repeatable_tie_break_and_changed_seed():
    s=SculptSession([],seed=999)
    a,rep=s.rank(k=100)
    b,_=s.rank(k=100)
    assert a.head(100)['number'].tolist()==b.head(100)['number'].tolist()
    c,_=SculptSession([],seed=1000).rank(k=100)
    assert a.head(100)['number'].tolist()!=c.head(100)['number'].tolist()
    assert rep['kept']==100_000


def test_basic_and_history_detection_uses_only_past():
    hist=['00010','00011','00012','00013','00014']
    cfg=Configuration(indicators=('sum',),transforms=('raw',),
        patterns=('strict_up',),windows=(3,),max_total_remove=.99,min_keep=10)
    knives,default=knives_from_history(hist,cfg,
        basic=[BasicConstraint('sum',maximum=25)])
    assert any(k.source=='basic' for k in knives)
    assert any(k.source.startswith('pattern') for k in knives)
    assert len(default)>=1
    s=SculptSession(knives,enabled=default)
    assert s.sculpt().audit['kept']<100_000


def test_walkforward_full_space_keeps_actual_out_of_training(monkeypatch):
    hist=[f'{i*37%100000:05d}' for i in range(15)]
    cfg=Configuration(indicators=('digit_1',),transforms=('raw',),
        patterns=('constant',),windows=(3,),max_rules=5)
    report=rolling_sculpt_backtest(hist,cfg,warmup=10,max_periods=2,k=100)
    assert report['periods']==2
    assert report['fair_expected_hits']==pytest.approx(.002)
    assert report['exploratory_only']
    assert all(row['rank']>=1 for row in report['details'])


def test_preserved_protected_number_selected_before_excluded():
    s=SculptSession([knife('a',0,99_999)])
    s.protect('00128')
    assert s.sculpt().kept_mask[128]
    table,_=s.rank(k=2)
    assert '00128' in table.head(2)['number'].tolist()


def test_manual_score_first_mode_does_not_claim_probability():
    s=SculptSession([knife('a',0,200)])
    df, meta=s.rank(k=100,locked_kept_first=False)
    assert len(df)==100000 and int(df['selected_top_k'].sum())==100
    assert meta['selection_policy']=='score_first'
    assert meta['statistical_status']=='uncalibrated_research_preferences'


def test_rule_weight_is_undoable_and_not_a_probability():
    s=SculptSession([knife('a',0,100,weight=1)])
    old=s.sculpt().penalty.copy()
    s.set_weight('a',2.5)
    assert np.all(s.sculpt().penalty[:100] == 2.5)
    assert s.undo()
    assert np.array_equal(s.sculpt().penalty,old)
    with pytest.raises(ValueError): s.set_weight('a',float('nan'))


def test_pinned_number_always_enters_final_k_even_if_there_are_many_kept():
    s=SculptSession([knife('a',0,100)])
    s.protect('00012')
    df,_=s.rank(k=1)
    assert df.iloc[0]['number']=='00012'
    s.protect('00013')
    with pytest.raises(ValueError): s.rank(k=1)
