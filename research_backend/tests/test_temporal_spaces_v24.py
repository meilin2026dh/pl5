import numpy as np
import pytest
from pailie5.nine_spaces_v24 import (
    TemporalSpec, temporal_proposal,compose_temporal,walk_forward_temporal,Rule,Spaces,N,
)

def test_repeat_sum_activates_and_exact_mass():
    hist=['00011','00011','00011','00011']
    spec=TemporalSpec('repeat_sum','sum_span','sum',window=4)
    p=temporal_proposal(hist,spec)
    assert p['status']=='candidate'
    assert p['next_value']==2
    assert p['affected_count']==15
    assert p['null_mass']==pytest.approx(15/N)
    assert p['proposal']['op']=='eq'

def test_arithmetic_and_unreachable_extension():
    s=TemporalSpec('slope','sum_span','sum',window=3,pattern='arithmetic')
    a=temporal_proposal(['00001','00002','00003'],s)
    assert a['status']=='candidate' and a['next_value']==4
    empty=temporal_proposal(['99997','99998','99999'],s)
    assert empty['status']=='impossible_extension'

def test_alternation_and_periodicity():
    x=['00001','00003','00001','00003']
    a=temporal_proposal(x,TemporalSpec('a','sum_span','sum',window=4,pattern='alternating'))
    b=temporal_proposal(x,TemporalSpec('b','sum_span','sum',window=4,pattern='periodic',period=2))
    assert a['next_value']==b['next_value']==1
    assert temporal_proposal(['00001','00002','00003','00004'],TemporalSpec('c','sum_span','sum',window=4))['status']=='no_pattern'

def test_dynamic_family_disallowed_for_historical_pattern():
    with pytest.raises(ValueError,match='动态'):
        TemporalSpec('bad','hot50','pca_reconstruction_error')
    with pytest.raises(ValueError,match='动态'):
        TemporalSpec('bad','markov2','surprisal')

def test_rule_union_and_strict_not_refilled():
    history=['00011']*6
    spec=TemporalSpec('repeat_sum','sum_span','sum',window=4)
    r=compose_temporal(history,[],[spec],budget=100,seed=3,base_numbers=['00000','00003','00011'])
    assert r['active_temporal_rules']==1
    assert r['strict_remaining']==2
    assert '00011' not in r['strict_numbers']
    assert len(r['ranked_numbers'])==3
    assert r['ranked_exact_random_coverage']==pytest.approx(3/N)

def test_walk_forward_recomputes_without_future():
    history=['00011']*31+['00030','00040','00050']
    spec=TemporalSpec('same','sum_span','sum',window=3)
    a=walk_forward_temporal(history[:33],[],[spec],min_train=30,last_n=2,budget=10,seed=17)
    b=walk_forward_temporal(history,[],[spec],min_train=30,last_n=3,budget=10,seed=17)
    assert a['rows']==b['rows'][:2]
    assert a['rows'][0]['active_temporal_rules']==1
    assert a['rows'][1]['active_temporal_rules']==0

def test_invalid_temporal_metrics_and_short_history():
    p=temporal_proposal(['00000'],TemporalSpec('s','steps','abs_sum',window=3))
    assert p['status']=='insufficient_history'
    with pytest.raises(ValueError,match='未知指标'):
        temporal_proposal(['00000']*4,TemporalSpec('s','steps','no_field'))

def test_metric_distribution_exact_and_nonuniform():
    from pailie5.nine_spaces_v24 import describe_metric
    r=describe_metric('mod3','road_key')
    assert r['different_values']==243
    assert r['min_bucket_count']==243  # 3^5
    assert r['max_bucket_count']==1024
    assert len(r['top_buckets'])==8
    assert r['top_buckets'][0]['random_null_mass']==pytest.approx(.01024)
