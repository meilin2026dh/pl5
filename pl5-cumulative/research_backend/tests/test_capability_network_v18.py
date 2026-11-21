import hashlib
import json
import numpy as np
import pytest
from pailie5.capability_network import (
    Capability, CapabilityRegistry, bootstrap, grow, metric_numpy,metric_python,
    predict_pattern,run_pipeline,check_numbers,N,validate,
)

@pytest.fixture
def db(tmp_path):
    reg=CapabilityRegistry(tmp_path/'aan.sqlite')
    yield reg
    reg.close()


def test_bootstrap_idempotent_and_cards(db):
    assert len(bootstrap(db)) == 8
    assert bootstrap(db) == []
    nodes=db.graph()['nodes']
    assert len(nodes) == 8
    assert nodes[0]['execution_policy']=='allowlisted_builtin_only'
    assert nodes[0]['predictive_status']=='UNVERIFIED'


def test_formula_python_numpy_crosscheck():
    specs=[{'metric':'sum'},{'metric':'span'},{'metric':'odd_count'},
           {'metric':'distinct_count'},{'metric':'sum_mod','mod':7},
           {'metric':'position_digit','position':3},
           {'metric':'position_diff','position':4,'other_position':1},
           {'metric':'inversions'}]
    universe=np.arange(100000)
    for p in specs:
        values=metric_numpy(universe,p)
        assert len(values)==N
        for i in (0,9,118,12345,99000,99999):
            assert values[i]==metric_python(f'{i:05d}',p)


def test_arithmetic_and_repeat_prediction():
    assert predict_pattern([18,20,22],{'name':'arithmetic','window':3})['predicted']==24
    assert predict_pattern([2,2,2],{'name':'repeat','window':3})['predicted']==2
    assert not predict_pattern([18,20,21],{'name':'arithmetic','window':3})['active']
    assert predict_pattern([1,2,1,2],{'name':'alternate','window':4})['predicted']==1
    assert predict_pattern([3,7,3,7],{'name':'cycle','window':4,'lag':2})['predicted']==3


def test_grow_is_bounded_and_idempotent(db):
    assert len(grow(db,limit=5))==5
    assert len(db.all())==8+10
    assert len(grow(db,limit=5))==5
    assert len(db.all())==8+20
    assert not db.gaps('anti_filter')['missing']
    assert all(x['research_only'] for x in grow(db,limit=2))


def test_scientific_report_no_predictive_claim(db):
    grow(db,limit=1)
    target='pl5.metric.sum.anti_repeat_3'
    report=run_pipeline(db,target,['00001','00001','00001'])
    assert report['excluded']==5
    assert report['kept']==99995
    assert report['predictive_advantage']=='NOT_ESTABLISHED'
    assert len(report['mask_sha256'])==64
    assert len(db.plan(target))==3
    assert report['receipt_id']==run_pipeline(db,target,['00001']*3)['receipt_id']
    assert run_pipeline(db,target,['00001','00002','00001'])['excluded']==0


def test_semantics_and_dependencies_reject(db):
    bootstrap(db)
    with pytest.raises(ValueError):
        db.add(Capability('pl5.bad.dep','bad','1.0.0','pattern',('missing',),
                          {'name':'repeat','window':3},'manual'))
    with pytest.raises(ValueError):
        db.add(Capability('pl5.bad.script','bad','1.0.0','exec',(),{},'manual'))
    with pytest.raises(ValueError):
        db.add(Capability('pl5.bad.mod','bad','1.0.0','metric',(),{'metric':'sum_mod','mod':0},'manual'))
    with pytest.raises(ValueError):
        db.add(Capability('pl5.bad.copy','copy','1.0.0','metric',(),{'metric':'sum'},'manual'))


def test_immutable_catalog_and_integrity(db):
    bootstrap(db)
    original=db.all()['pl5.metric.sum']
    with pytest.raises(ValueError):
        db.add(Capability(original.id,'edited','1.0.0','metric',(),{'metric':'sum'},'manual'))
    db.db.execute('UPDATE capabilities SET payload=? WHERE id=?', ('{}',original.id))
    db.db.commit()
    with pytest.raises(RuntimeError): db.all()


def test_no_bad_numbers(db):
    grow(db,limit=1)
    for rows in [['1234'],['00000','abcde'],[]]:
        with pytest.raises(ValueError):run_pipeline(db,'pl5.metric.sum.anti_repeat_3',rows)


def test_mask_union_and_guard(db):
    grow(db,limit=2)
    a='pl5.metric.sum.anti_repeat_3'
    b='pl5.metric.sum.anti_arithmetic_3'
    merge=Capability('pl5.compose.a_b','组合','1.0.0','merge_masks',(a,b),{},'local')
    db.add(merge)
    r=run_pipeline(db,merge.id,['00000','00001','00002'])
    assert r['excluded']>0
    assert r['excluded']<100000
    assert db.graph()['count']==13


def test_status_revocation_guard(db):
    grow(db,limit=1)
    key='pl5.metric.sum.anti_repeat_3'
    # No registry transition from data-dependent claims to approved predictive status.
    assert all(x.status=='research' for x in db.all().values())
    with pytest.raises(ValueError):
        db.add(Capability('pl5.fake.proof','fake','1.0.0','metric',(),
                          {'metric':'sum_mod','mod':23},'manual',evidence='validated'))


def test_esse_exploratory_composition_only(db):
    from pailie5.capability_network import research_knife
    from pailie5.sculpting import SculptSession
    grow(db,limit=1)
    knife,report=research_knife(db,'pl5.metric.sum.anti_repeat_3',['00001']*3)
    assert knife.excluded.shape==(100000,)
    assert knife.source=='AAN-experiment'
    exploration=SculptSession([knife],mode='explore')
    assert exploration.sculpt().audit['kept']==99995
    exploration.set_enabled(knife.key,False)
    assert exploration.sculpt().audit['kept']==100000
    # The same unreviewed source MUST NOT gain strict-mode authority.
    strict=SculptSession([knife],mode='strict',approved_keys=())
    assert strict.sculpt().audit['kept']==100000


def test_growth_expands_metric_grammar_after_core_saturation(db):
    for _ in range(8):
        assert len(grow(db,limit=6))==6
    before=len(db.all())
    assert before==8+8*12
    result=grow(db,limit=1)
    assert len(result)==1
    assert len(db.all())==before+3
    assert len(grow(db,limit=1))==1
