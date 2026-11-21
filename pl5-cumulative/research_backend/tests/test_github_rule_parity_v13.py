"""Independent parity tests for sourced GitHub basic rule definitions."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pailie5.github_rule_parity import N, digits_table, metric_values, evaluate_basic, SUPPORTED
from pailie5.integration_bridge import encode_mask, run_bridge, ContractError


def test_full_universe_and_known_values():
    d=digits_table()
    assert d.shape == (100000,5)
    assert d[127].tolist() == [0,0,1,2,7]
    assert int(metric_values('sum')[127]) == 10
    assert int(metric_values('span')[127]) == 7
    assert int(metric_values('odd')[127]) == 2
    assert int(metric_values('prime')[127]) == 3
    assert int(metric_values('distinct')[127]) == 4
    assert metric_values('repeat')[127] == '2111'
    assert int(metric_values('consecutive')[127]) == 2
    assert metric_values('repeat')[0] == '5'
    assert int(metric_values('consecutive')[999]) == 0
    assert len(SUPPORTED) == 12

@pytest.mark.parametrize('kind,values,expected',[
    ('sum',[10],True),('tail',[0],True),('span',[7],True),
    ('odd',[2],True),('big',[1],True),('prime',[3],True),
    ('distinct',[4],True),('repeat',['2111'],True),
    ('consecutive',[2],True),('sumMod3',[1],True),
    ('dan',[1,7],True),('kill',[4,9],True),
])
def test_canonical_all_universe_rule(kind,values,expected):
    rule={'kind':kind,'mode':'include','values':values}
    mask=evaluate_basic(rule)
    assert mask.shape == (N,) and mask.dtype==np.bool_
    assert bool(mask[127]) == expected
    inverted=evaluate_basic({**rule,'mode':'exclude'})
    assert np.array_equal(inverted,~mask)


def example_request():
    base=np.ones(N,dtype=bool)
    spec={'id':'sum10','kind':'sum','mode':'include','values':[10]}
    kept=evaluate_basic(spec)
    return {
      'schema':'pl5-esse-bridge-v1','protocol_upgrade':'v13_verified',
      'combination':'strict','k':10,'seed':11,
      'base':encode_mask(base),
      'rules':[{'id':'sum10','label':'sum','group':'sum','enabled':True,
                'rule_spec':spec,'kept':encode_mask(kept)}],
      'strict_kept':encode_mask(kept),
      'expected_strict_keep':int(kept.sum()),
    }


def test_full_independent_basic_parity_and_source_protection():
    report=run_bridge(example_request())
    assert report['full_mask_parity_verified'] is True
    assert report['independent_rule_count']==1
    assert report['independent_rule_ids']==['sum10']
    assert report['unverified_rule_types']==[]
    assert report['source_guard'] is True
    assert report['selected_count']==10
    assert report['statistical_status']=='NO_PREDICTIVE_ADVANTAGE_ESTABLISHED'


def test_detect_wrong_rule_even_if_counts_equal():
    payload=example_request()
    b=payload['rules'][0]['kept']
    m=evaluate_basic(payload['rules'][0]['rule_spec']).copy()
    a=int(np.flatnonzero(m)[0]); c=int(np.flatnonzero(~m)[0]);m[a]=False;m[c]=True
    payload['rules'][0]['kept']=encode_mask(m)
    payload['strict_kept']=encode_mask(m)
    with pytest.raises(ContractError,match='完整位图不一致'):
        run_bridge(payload)


def test_detect_strict_intersection_same_count_wrong_numbers():
    payload=example_request()
    rule=payload['rules'][0]
    spec=rule.pop('rule_spec')
    correct=evaluate_basic(spec)
    wrong=correct.copy()
    a=int(np.flatnonzero(wrong)[0]); c=int(np.flatnonzero(~wrong)[0]);wrong[a]=False;wrong[c]=True
    payload['strict_kept']=encode_mask(wrong)
    with pytest.raises(ContractError,match='最终TypeScript严格AND位图'):
        run_bridge(payload)


def test_v13_requires_strict_mask():
    payload=example_request()
    del payload['strict_kept']
    with pytest.raises(ContractError,match='完整位图'):
        run_bridge(payload)


def test_unknown_rule_remains_auditable_but_unverified():
    payload=example_request()
    payload['rules'][0]['rule_spec']={'id':'sum10','kind':'advancedUnknown', 'mode':'include','values':[10]}
    report=run_bridge(payload)
    assert report['independent_rule_count']==0
    assert 'advancedUnknown' in report['unverified_rule_types']


def test_canonical_github_vendor_hash():
    vendor=Path(__file__).resolve().parents[2]/'github_vendor'
    known={
       'server/provider.ts':'43f2c05896d728f97fdcc64a7b64988e3785b88c',
       'src/lib/candidates.ts':'58e63cbda68c9317519cbb8f339f2d78653a2c78',
       'src/domain/math.ts':'5d3725d839d29375d3ab785849998bba87891717',
       'src/domain/backtest.ts':'a71ecd6166d867e46e3f36d29cce758ba4e6a79b',
    }
    for rel,sha in known.items():
        data=(vendor/rel).read_bytes()
        assert hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()==sha
