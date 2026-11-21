import math
import numpy as np
import pytest
from pailie5.nine_spaces_v24 import (N, Spaces, Rule, features_15bit, reconstruct_signed,
    comparison, compose, walk_forward, capability_cards, predefined_exploratory_rules)
from pailie5.space_mapping import encoding_of, inverse_encoding
from pailie5.engine import DIGITS

DEMO=[f'{(i*7919 + i*i*17)%100000:05d}' for i in range(85)]


def test_all_families_cards():
    assert len(capability_cards())==9
    assert all(x['predictive_advantage']=='unverified' for x in capability_cards())


def test_attributes_are_15bit_and_only_7_codes_realizable():
    bits,codes=features_15bit()
    assert bits.shape==(N,15)
    assert codes.shape==(N,5)
    assert set(np.unique(codes))=={0,1,2,4,5,6,7}
    assert list(codes[0])==[0]*5
    assert np.array_equal(codes[12345],[4,1,5,0,7])  # 1..5真实对应的型码
    assert len(np.unique(Spaces().get('attributes')['code_signature']))==7**5


def test_sum_tail_is_dependent_on_sum():
    f=Spaces().get('sum_span')
    assert np.all(f['sum_tail']==f['sum']%10)
    assert f['sum'][12345]==15
    assert f['span'][12345]==4


def test_road_counts_243_and_nonuniform_class_sizes():
    f=Spaces().get('mod3')
    keys,cnt=np.unique(f['road_key'],return_counts=True)
    assert len(keys)==243
    assert cnt.min()==3**5
    assert cnt.max()==4**5
    assert cnt.sum()==N
    assert f['all_same'].sum()==4**5+3**5+3**5


def test_mod3_transitions_not_leaking_last_as_future():
    a=Spaces(DEMO[:50]).get('mod3')['transition_log_score']
    b=Spaces(DEMO[:50]+['99999']).get('mod3')['transition_log_score']
    assert np.all(np.isfinite(a)) and np.all(np.isfinite(b))
    assert not np.array_equal(a,b)


def test_steps_recoverable_with_signed_plus_first_not_abs():
    f=Spaces().get('steps')
    assert f['abs_signature'][12345]==1111
    assert f['signed_sum'][12345]==4
    assert reconstruct_signed(1,[1,1,1,1])=='12345'
    assert reconstruct_signed(2,[-1,1,-1,1])=='21212'
    assert f['abs_signature'][12345]==f['abs_signature'][54321]
    with pytest.raises(ValueError): reconstruct_signed(0,[-1,0,0,0])


def test_symmetric_exact_state_count_and_center_retained():
    f=Spaces().get('symmetric')
    assert f['outer_sum'][12345]==6
    assert f['center'][12345]==3
    assert len(np.unique(f['outer_pair_key']))==55
    assert len(np.unique(f['symmetric_signature']))==55*55*10
    assert f['symmetric_signature'][12345]==f['symmetric_signature'][52341]


def test_hot50_candidate_dependent_sparse_embedding():
    f=Spaces(DEMO).get('hot50')
    assert len(f['pca_reconstruction_error'])==N
    assert np.all(f['pca_reconstruction_error']>=0)
    assert np.all(np.isfinite(f['sum_negative_log_hotness']))
    assert len(np.unique(f['sum_negative_log_hotness']))>1
    with pytest.raises(ValueError): Spaces(DEMO[:29]).get('hot50')


def test_markov_smoothed_and_contextual():
    f=Spaces(DEMO).get('markov2')
    assert np.isfinite(f['log_score']).all()
    assert f['transition_support'].min()>=0
    assert np.exp(f['log_score']).min()>0
    with pytest.raises(ValueError): Spaces(DEMO[:2]).get('markov2')


def test_combination_mapping_and_histogram_56():
    f=Spaces().get('combination')
    assert len(np.unique(f['group_distribution_key']))==math.comb(8,3)==56
    assert f['pick23_sum'].shape==(N,)
    for no in ['00000','00128','12345','99999']:
        assert inverse_encoding(encoding_of(no,'pick23_6'),'pick23_6')==no


def test_comparison_guardrails():
    a=np.array([0,1,2,3])
    assert np.array_equal(comparison(a,'between',[1,2]),[False,True,True,False])
    with pytest.raises(ValueError):comparison(a,'between',[3,2])
    with pytest.raises(ValueError):comparison(a,'in',1)


def test_multirule_union_no_probabilities_exaggerated():
    rules=predefined_exploratory_rules()
    result=compose(DEMO, rules,budget=100,seed=1)
    assert result['base']==100000
    assert len(result['ranked_numbers'])==100
    assert len(set(result['ranked_numbers']))==100
    assert result['ranked_exact_random_coverage']==.001
    assert result['fair_each_probability']==.00001
    assert sum(v['marginal_excluded'] for v in result['audit'])==100000-result['strict_remaining']
    assert all(x['raw_excluded']>=x['marginal_excluded'] for x in result['audit'])
    assert len(result['overlaps'])==10


def test_external_base_never_crossed_or_filled_with_outside():
    base=['00000','00128','99999']
    r=compose(DEMO,[Rule('ban0','sum_span','sum','eq',0)],budget=100,base_numbers=base)
    assert r['base']==3
    assert set(r['ranked_numbers'])==set(base)
    assert '00000' not in r['strict_numbers']
    assert len(r['strict_numbers'])==2
    assert r['ranked_exact_random_coverage']==.00003


def test_retention_logic_and_duplicate_ids():
    r=compose([], [Rule('allow','sum_span','sum','eq',0,'retain')],budget=10)
    assert r['strict_remaining']==1
    assert r['strict_numbers']==['00000']
    with pytest.raises(ValueError):compose([], [Rule('x','sum_span','sum','eq',1)]*2)


def test_rolling_is_frozen_past_no_future():
    rules=[Rule('odd5','attributes','odd_count','eq',5)]
    a=walk_forward(DEMO[:45],rules,min_train=30,last_n=5,budget=100)
    b=walk_forward(DEMO[:45]+['99999'],rules,min_train=30,last_n=6,budget=100)
    assert a['rows']==b['rows'][:5]
    assert a['expected_random_hits']==pytest.approx(.005)


def test_road_group_actual_small_nonuniform_not_equal_to_probabilities():
    f=Spaces().get('mod3')
    count0=np.sum(f['road_key']==0)
    countall2=np.sum(f['road_key']==242)
    assert count0==4**5 and countall2==3**5
    assert count0/N != countall2/N
