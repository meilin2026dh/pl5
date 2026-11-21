"""V2.9 finite-domain primitive induction: mathematical, security and split tests."""
import copy
import json
import math
import sqlite3
import numpy as np
import pytest
from pailie5.primitive_invention_v29 import (
    DIGITS, N, FAMILIES, Primitive, _baseline_partitions, _canonical_partition,
    discover, fit_primitive, history_array, induce_table, pmf, register, score_evidence, study
)


def draws(seed=8,n=320,bias=False):
    rng=np.random.default_rng(seed)
    d=rng.integers(0,10,size=(n,5))
    if bias:d[:,1]=d[:,0]
    return [''.join(map(str,row)) for row in d]


def test_digits_zero_padding_and_full_space():
    assert DIGITS.shape==(100000,5)
    assert DIGITS[0].tolist()==[0,0,0,0,0]
    assert DIGITS[127].tolist()==[0,0,1,2,7]
    assert DIGITS[-1].tolist()==[9,9,9,9,9]


@pytest.mark.parametrize('invalid', [['1234']*230,['12x45']*230,[],['00000']*189])
def test_history_invalid(invalid):
    with pytest.raises(ValueError):history_array(invalid)


@pytest.mark.parametrize('family',FAMILIES)
@pytest.mark.parametrize('classes',[3,4])
def test_induced_table_valid(family,classes):
    arr=history_array(draws())
    t=induce_table(arr,(0,1),family,classes)
    assert t.shape==(10,10)
    assert set(t.ravel())==set(range(classes))
    assert _canonical_partition(t) not in _baseline_partitions(classes)


def test_full_scalar_reference_and_semantics():
    arr=history_array(draws())
    op=discover(arr[:180],maximum=1)[0][0]
    assert op.full_crosscheck()['checked']==N
    assert op.call(0,1)==op.table[1]
    assert op.vector(DIGITS[[0,127,99999]]).shape==(3,)
    assert op.card()['status']=='research_only'
    assert op.card()['table_sha256']==op.table_sha256
    assert sum(op.card()['properties']['occupied_output_classes'] for _ in [0])==op.levels


def test_invalid_finite_operator_rejected():
    with pytest.raises(ValueError):Primitive((0,1),'spectral_bilinear',3,(0,)*100,'x',1.0)
    with pytest.raises(ValueError):Primitive((0,0),'spectral_bilinear',3,tuple(i%3 for i in range(100)),'x',1.0)
    with pytest.raises(ValueError):Primitive((0,1),'evil_python',3,tuple(i%3 for i in range(100)),'x',1.0)
    with pytest.raises(ValueError):Primitive((0,1),'spectral_bilinear',3,tuple([3]+[i%3 for i in range(1,100)]),'x',1.0)


def test_novel_and_reproducible_invention():
    arr=history_array(draws(n=290))
    one,rejected=discover(arr[:200],maximum=20)
    two,_=discover(arr[:200],maximum=20)
    assert len(one)==20
    assert [x.identity for x in one]==[x.identity for x in two]
    assert len(set(x.identity for x in one))==len(one)
    assert any(x.table_sha256 for x in one)
    assert all(x.stability<=1 for x in one)


def test_pmf_is_normalized_and_e_null_integrates_to_one():
    hist=history_array(draws(n=300))
    op=discover(hist[:200],maximum=1)[0][0]
    fit=fit_primitive(op,hist[:200])
    for mixture in (0.25,0.5,1):
        p=pmf(op,fit,mixture)
        assert p.min()>0
        assert np.isclose(p.sum(),1,atol=1e-12)
        assert np.isclose((N*p).mean(),1,atol=1e-12)
        assert np.isfinite(score_evidence(op,fit,hist[200:260],mixture)['log_e_value'])


def test_sealed_holdout_cannot_influence_model_selection():
    rows=draws(n=320)
    r1=study(rows,seed=20,maximum=8,validation_periods=50,holdout_periods=40)
    changed=rows[:-40]+['99999']*40
    r2=study(changed,seed=20,maximum=8,validation_periods=50,holdout_periods=40)
    assert r1['selected_operator']==r2['selected_operator']
    assert r1['validation_experiments']==r2['validation_experiments']
    assert r1['cards']==r2['cards']
    assert r1['history_sha256']!=r2['history_sha256']


def test_fair_demo_abstains():
    r=study(draws(seed=20261102,n=500),maximum=12,validation_periods=60,holdout_periods=50)
    assert not r['validation_gate']['passed']
    assert r['selected_operator'] is None
    assert r['model_probability_sum']==pytest.approx(1.0)
    assert len(set(r['experimental_top_k']))==100
    assert all(len(s)==5 for s in r['experimental_top_k'])


def test_known_nonuniform_synthetic_can_be_detected():
    r=study(draws(seed=20261102,n=800,bias=True),maximum=40,validation_periods=90,holdout_periods=60)
    assert r['validation_gate']['passed']
    assert r['sealed_holdout']['mean_log_gain']>0
    assert r['tests_counted']==3*len(r['cards'])
    assert r['selected_operator']['log_e_value'] >= r['familywise_log_e_threshold']
    assert r['promotion'].startswith('research_only')


def test_append_only_registry(tmp_path):
    r=study(draws(n=270),maximum=3,validation_periods=40,holdout_periods=30,budget=20)
    path=tmp_path/'database.sqlite'
    n=register(r,path);assert n>0
    assert register(r,path)==0
    with sqlite3.connect(path) as db:
        assert db.execute('select count(*) from v29_primitives').fetchone()[0]==n

def test_validation_and_budget_guards():
    with pytest.raises(ValueError):study(draws(n=250),budget=101)
    with pytest.raises(ValueError):study(draws(n=250),validation_periods=39)
    with pytest.raises(ValueError):discover(history_array(draws())[:119])


def test_bcse_clauses_only_from_selected_operator():
    from pailie5.primitive_invention_v29 import bcse_research_clauses
    hist=history_array(draws(n=300))
    op=discover(hist[:200],maximum=1)[0][0]
    fit=fit_primitive(op,hist[:200])
    clauses=bcse_research_clauses(op,fit,.5)
    assert len(clauses)==op.levels
    assert all(x['mode']=='research_only_not_authorized_for_esse' for x in clauses)
    assert sum(x['candidate_share'] for x in clauses)==pytest.approx(1)
    assert all(x['model_conditional_ratio_95pct_interval'][0]<=x['posterior_ratio']<=x['model_conditional_ratio_95pct_interval'][1] for x in clauses)


def test_aan_research_pipeline_accepts_new_primitive_without_granting_authority(tmp_path):
    from pailie5.capability_network import CapabilityRegistry,Capability,metric_numpy,metric_python,run_pipeline
    from pailie5.primitive_invention_v29 import register_aan_primitives
    rows=draws(n=270)
    r=study(rows,maximum=2,validation_periods=40,holdout_periods=30,budget=20)
    path=tmp_path/'aan.sqlite'
    assert register_aan_primitives(r,path)==len(r['cards'])
    assert register_aan_primitives(r,path)==0
    opid=r['cards'][0]['id']+'.'+r['cards'][0]['train_fingerprint'][:12]
    db=CapabilityRegistry(path)
    try:
        primitive=db.all()[opid]
        assert primitive.status=='research' and primitive.evidence=='unverified'
        sample=np.array([0,127,99999],dtype=np.int64)
        p=primitive.params
        assert np.array_equal(metric_numpy(sample,p),
            [metric_python(f'{n:05d}',p) for n in sample])
        training_rows=rows[:r['splits']['train_periods']]
        with pytest.raises(ValueError,match='前视'):
            run_pipeline(db,opid,training_rows[:-1])
        with pytest.raises(ValueError,match='前缀'):
            run_pipeline(db,opid,['99999']+training_rows[1:])
        got=run_pipeline(db,opid,training_rows)
        assert got['predictive_advantage']=='NOT_ESTABLISHED'
        assert got['kind']=='metric' and len(got['output'])==len(training_rows)
        pattern=Capability('pl5.test.primitive.pattern','research','1.0.0','pattern',
                 (opid,),{'name':'repeat','window':3},'unit-test')
        db.add(pattern)
        filt=Capability('pl5.test.primitive.anti','research','1.0.0','anti_filter',
                 (opid,pattern.id),{},'unit-test')
        db.add(filt)
        rs=run_pipeline(db,filt.id,training_rows)
        assert 0<=rs['excluded']<=100000
        assert rs['predictive_advantage']=='NOT_ESTABLISHED'
    finally:db.close()


def test_cli_discovers_and_aan_registers(tmp_path):
    import subprocess,sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    out=tmp_path/'report.json'
    reg=tmp_path/'aan.sqlite'
    cmd=[sys.executable,'research_v29.py','discover','--maximum','2','--report',str(out),'--aan-registry',str(reg)]
    cp=subprocess.run(cmd,cwd=root,capture_output=True,text=True,timeout=20)
    assert cp.returncode==0,cp.stderr
    r=json.loads(out.read_text())
    assert r['aan_research_primitives_inserted']==2
    assert len(r['cards'])==2
