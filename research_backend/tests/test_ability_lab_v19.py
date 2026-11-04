"""V1.9 goal-driven, independently reimplemented bounded algorithm research."""
from __future__ import annotations
import json
import sqlite3
import numpy as np
import pytest
from pailie5.ability_lab_v19 import (
  AbilityLab, Goal, validate_expr, expression_numpy, expression_python,
  feature_signature, propose_expr, backtest_anti, plan_goal, N,
)
from pailie5.capability_network import CapabilityRegistry, metric_numpy, metric_python, run_pipeline, research_knife
from pailie5.sculpting import SculptSession


def test_expression_all_100k_two_implementations():
    expressions=[propose_expr(x,idx) for x in ('cross_position','modular_structure','sequential_geometry','hybrid_features') for idx in (0,6,132)]
    nums=np.arange(N)
    for expr in expressions:
        full=expression_numpy(nums,expr)
        assert full.shape==(N,)
        check=np.array([expression_python(f'{int(n):05d}',expr) for n in (0,7,1200,12345,99999)])
        assert np.array_equal(full[[0,7,1200,12345,99999]],check)


def test_injection_depth_schema_guard():
    for bad in ({'op':'__import__','source':'os.system'},
                {'op':'position','index':True},
                {'op':'constant','value':10000000},
                {'op':'mod','arg':{'op':'sum'},'divisor':0},
                {'op':'add','left':{'op':'sum'},'right':{'op':'sum'},'unexpected':1},
                {'op':'abs','arg':{'op':'abs','arg':{'op':'abs','arg':{'op':'abs','arg':{'op':'abs','arg':{'op':'sum'}}}}}}):
        with pytest.raises(ValueError):validate_expr(bad)
    with pytest.raises(ValueError):expression_numpy(np.array([100000]),{'op':'sum'})
    with pytest.raises(ValueError):expression_python('1234',{'op':'sum'})


def test_partition_duplicate_detects_bijective_relabel():
    x=np.arange(100000)%10
    assert feature_signature(x)==feature_signature((x+3)%10)
    assert feature_signature(x)!=feature_signature(x%2)


def test_goal_and_immutable_cycle(tmp_path):
    path=tmp_path/'lab.sqlite'
    assert plan_goal(path,Goal('cross_position'))['gaps']['novel_metric_needed']
    with AbilityLab(path) as lab:
        a=lab.run(Goal('cross_position',2),cycle_key='once')
        b=lab.run(Goal('cross_position',2),cycle_key='once')
        assert a==b and a['count']==2
        assert lab.latest()['total']==2
        with pytest.raises(ValueError):lab.run(Goal('modular_structure',1),cycle_key='once')
        assert lab.run(Goal('cross_position',1),cycle_key='next')['count']==1
    with AbilityLab(path) as lab:
        assert lab.latest()['total']==3


def test_workflow_runs_as_research_only(tmp_path):
    path=tmp_path/'run.sqlite'
    with AbilityLab(path) as lab:
        result=lab.run(Goal('hybrid_features',1),history=['00001','00001','00001','00001'],cycle_key='h1')
        assert result['count']==1
        row=lab.latest()['proposals'][0]['report']
        assert row['full_space_parity'] and row['evaluated_numbers']==N
        assert row['historical_exploration']['status']=='exploratory'
        target=result['created'][0]['filter_id']
    db=CapabilityRegistry(path)
    try:
        assert len(db.plan(target))==3
        r=run_pipeline(db,target,['00001']*3)
        assert r['excluded']>=0 and r['excluded']<=N
        assert r['predictive_advantage']=='NOT_ESTABLISHED'
        knife,_=research_knife(db,target,['00001']*3)
        assert SculptSession([knife],mode='strict',approved_keys=()).sculpt().audit['kept']==N
    finally:db.close()


def test_no_official_paper_reproduction_claim(tmp_path):
    with AbilityLab(tmp_path/'p.sqlite') as lab:
        r=lab.run(Goal('modular_structure',1,source='论文线索待确认'))
        report=lab.latest()['proposals'][0]['report']
        assert r['approval']=='NOT_AUTOMATIC'
        assert report['source']=='论文线索待确认'
        assert report['predictive_advantage']=='NOT_ESTABLISHED'
        assert 'engineered_research_only'==report['status']


def test_short_history_and_history_cutoff():
    v=np.array([0,1,0,1,0,1],dtype=np.int64)
    f=np.repeat(np.arange(10),10000)
    a=backtest_anti(v,f,window=3,trials=2)
    assert a['evaluated_periods']==2
    assert a['active_periods']==0
    assert backtest_anti([1,1,1],f,window=3)['status']=='insufficient'
    b=backtest_anti([1,1,1,1],f,window=3)
    assert b['active_periods']==1 and b['observed_exclusions']==1
    assert b['expected_exclusions_under_uniform']==0.1


def test_old_capability_grow_survives_new_expression(tmp_path):
    from pailie5.capability_network import grow
    with AbilityLab(tmp_path/'old.sqlite') as lab:
        assert lab.run(Goal('cross_position',1))['count']==1
    db=CapabilityRegistry(tmp_path/'old.sqlite')
    try:
        assert grow(db,limit=2)
        assert len([x for x in db.all().values() if x.op=='metric'])>=1
    finally:db.close()


def test_does_not_allow_arbitrary_proposal_execution(tmp_path):
    # New capability records carry only allowlisted grammar, never source-code bodies.
    db=CapabilityRegistry(tmp_path/'safe.sqlite')
    try:
        from pailie5.capability_network import Capability
        with pytest.raises(ValueError):
            db.add(Capability('pl5.unsafe.script','bad','1.0.0','metric',(),
                        {'metric':'expr','expr':{'op':'exec','script':'open("secret")'}},'external'))
    finally:db.close()
