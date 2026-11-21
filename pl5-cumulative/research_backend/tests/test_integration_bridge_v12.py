import copy
import base64
import numpy as np
import pytest
from pailie5.integration_bridge import ContractError,SCHEMA,decode_mask,encode_mask,run_bridge

N=100000

def m(a,b):
    z=np.zeros(N,dtype=bool)
    z[a:b]=True
    return encode_mask(z)

def payload():
    return {"schema":SCHEMA,"combination":"strict","k":100,"seed":777,
            "base":m(100,600),"rules":[
                {"id":"sum","label":"和值","group":"basic","enabled":True,"kept":m(100,450)},
                {"id":"odd","label":"奇偶","group":"basic","enabled":True,"kept":m(200,600)}],
            "expected_strict_keep":250,
            "meta":{"history_source":"测试夹具，非官方数据","reference_issue":"26290"}}

def test_little_endian_roundtrip_and_leading_zeros():
    x=np.zeros(N,dtype=bool);x[[0,1,7,8,128,99999]]=True
    assert np.array_equal(decode_mask(encode_mask(x)),x)
    raw=base64.b64decode(encode_mask(x)['bits'])
    assert raw[:2]==bytes((0b10000011,0b00000001))

def test_two_knife_parity_order_and_source():
    r=run_bridge(payload())
    assert r['strict_keep_count']==250
    assert r['source_guard']
    assert r['selected_count']==100 and r['restored_for_quota']==0
    assert len(set(r['top_numbers']))==100
    assert all(200 <= int(n) < 450 for n in r['top_numbers'])
    assert r['steps'][0]['after']==500
    assert r['steps'][-1]['after']==250
    assert r['marginals'][0]['recoverable_if_disabled']==150
    assert r['fair_random_single_draw_coverage']==.001
    assert not r['history_source_verified_by_backend']

def test_clamps_quota_to_source_without_resurrecting_outside():
    p=payload();p['base']=m(100,120);p['rules']=[];p['expected_strict_keep']=20
    r=run_bridge(p)
    assert r['selected_count']==20
    assert all(100 <= int(x)<120 for x in r['top_numbers'])

def test_quota_repair_can_only_restore_inside_source():
    p=payload();p['rules']=[{"id":"tiny","label":"少量","group":"a","enabled":True,"kept":m(100,105)}];p['expected_strict_keep']=5
    r=run_bridge(p)
    assert r['selected_count']==100 and r['restored_for_quota']==95
    assert all(100 <= int(x)<600 for x in r['top_numbers'])

def test_detects_count_mismatch_sha_and_base_escape():
    p=payload();p['expected_strict_keep']=251
    with pytest.raises(ContractError,match='不一致'):run_bridge(p)
    p=payload();p['base']['sha256']='0'*64
    with pytest.raises(ContractError,match='SHA256'):run_bridge(p)
    p=payload();p['rules'][0]['kept']=m(0,450)
    with pytest.raises(ContractError,match='超出来源'):run_bridge(p)

def test_denies_soft_semantics_and_forged_approval():
    p=payload();p['combination']='atLeast'
    with pytest.raises(ContractError,match='严格AND'):run_bridge(p)
    p=payload();p['rules'][0]['evidence']='independently_verified'
    assert run_bridge(p)['statistical_status']=='NO_PREDICTIVE_ADVANTAGE_ESTABLISHED'

def test_duplicate_rule_or_bad_mask():
    p=payload();p['rules'][1]['id']='sum'
    with pytest.raises(ContractError,match='冲突'):run_bridge(p)
    p=payload();p['base']['bits']='??'
    with pytest.raises(ContractError,match='base64'):run_bridge(p)

def test_repeatability_and_seed_changes_only_ties():
    p=payload();a=run_bridge(p);b=run_bridge(p)
    assert a['top_numbers']==b['top_numbers']
    p['seed']=778;c=run_bridge(p)
    assert a['strict_keep_count']==c['strict_keep_count']
    assert a['top_numbers']!=c['top_numbers']

def test_traditional_metrics_against_independent_full_space_enumeration():
    """Python mirror of GitHub's published `metrics` definition; not TS execution."""
    from pailie5.engine import UNIVERSE
    arr = np.array([[int(c) for c in f'{n:05d}'] for n in UNIVERSE], dtype=np.int8)
    sums = arr.sum(axis=1)
    odd = (arr % 2).sum(axis=1)
    keep = (sums == 10) & (odd == 2)
    request = {"schema":SCHEMA,"combination":"strict","k":100,"seed":7,
               "base":encode_mask(np.ones(N,dtype=bool)),
               "rules":[{"id":"sum10","label":"和值10","group":"sum","enabled":True,"kept":encode_mask(sums==10)},
                        {"id":"odd2","label":"奇数2","group":"odd","enabled":True,"kept":encode_mask(odd==2)}],
               "expected_strict_keep":int(keep.sum()),"meta":{"history_source":"independent arithmetic fixture"}}
    r=run_bridge(request)
    assert r['strict_keep_count']==int(keep.sum())
    assert all(keep[int(n)] for n in r['top_numbers'])
