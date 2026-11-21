"""V3.7.22 scientific role separation, counterexamples, abstention, integrity."""
from __future__ import annotations

import inspect
import json
from pathlib import Path
import pytest
from pailie5.language_evolution_v3722 import (
    create_synthetic_task, invent, falsify, freeze, evaluate, propose_revision, finite_domain_certificate, _validate_spec,
    _evaluate_spec, _features, TASK_FAMILIES,
)
from pailie5.math_discovery_v3720 import read_cells


def fixture(tmp_path, family='cubic_sum', seed=3722):
    data=tmp_path/'task'; study=tmp_path/'study'
    create_synthetic_task(data,family=family,seed=seed)
    return data,study


def stages(data,study):
    p=invent(read_cells(data/'training.json'),study)
    c=falsify(study,read_cells(data/'challenge.json'))
    f=freeze(study,read_cells(data/'validation.json'))
    e=evaluate(study,read_cells(data/'holdout.json'))
    return p,c,f,e


@pytest.mark.parametrize('family',['cubic_sum','step_sum','square_difference','parity_difference'])
@pytest.mark.parametrize('seed',[3722,3723,3724])
def test_structured_development_tasks(tmp_path,family,seed):
    data,study=fixture(tmp_path,family,seed)
    p,c,f,e=stages(data,study)
    assert p['train_labels_only'] is True
    assert c['retrain_after_counterexample'] is False
    assert f['test_labels_used'] is False
    assert f['status']=='FROZEN',(family,seed,f['reason'],f['distinct_candidate_behaviours'])
    assert e['status']=='EVALUATED'
    assert e['holdout_errors']==0 and e['holdout_unknown']==0
    assert e['lottery_predictive_advantage']=='NOT_ESTABLISHED'



@pytest.mark.parametrize('seed',[3722,3723,3724,3725,3726])
def test_cubic_product_requires_coverage_not_forced_guess(tmp_path,seed):
    data,study=fixture(tmp_path,'cubic_product',seed)
    _,_,f,e=stages(data,study)
    if f['status']=='FROZEN':
        assert e['holdout_errors']==0 and e['holdout_unknown']==0
    else:
        assert f['reason']=='no_candidate_survives_challenge_and_validation'
        assert e['status']=='ABSTAIN' and e['holdout_errors'] is None

@pytest.mark.parametrize('family',['random_null','unstructured_interaction'])
@pytest.mark.parametrize('seed',[3722,3723,3724])
def test_difficult_families_abstain(tmp_path,family,seed):
    data,study=fixture(tmp_path,family,seed)
    p,c,f,e=stages(data,study)
    assert f['status']=='ABSTAIN',(family,seed,f)
    assert e['holdout_errors'] is None and e['holdout_accuracy'] is None
    assert not (study/'final_operator.json').exists()


def test_stage_apis_do_not_accept_holdout(tmp_path):
    for method in (invent,falsify,freeze):
        assert 'holdout' not in inspect.signature(method).parameters
    data,study=fixture(tmp_path)
    train=read_cells(data/'training.json')
    p=invent(train,study)
    assert all(item['spec']['training_sha256']==train.fingerprint for item in p['candidates'])
    assert len({tuple(p) for p in p['training_pairs']})==55


def test_no_coordinate_leakage(tmp_path):
    data,study=fixture(tmp_path)
    invent(read_cells(data/'training.json'),study)
    with pytest.raises(ValueError,match='leak'):
        falsify(study,read_cells(data/'training.json'))
    falsify(study,read_cells(data/'challenge.json'))
    with pytest.raises(ValueError,match='independent'):
        freeze(study,read_cells(data/'training.json'))
    freeze(study,read_cells(data/'validation.json'))
    with pytest.raises(ValueError,match='overlaps'):
        evaluate(study,read_cells(data/'training.json'))


def test_append_only_all_stages(tmp_path):
    data,study=fixture(tmp_path)
    train=read_cells(data/'training.json')
    invent(train,study)
    with pytest.raises(FileExistsError):invent(train,study)
    challenge=read_cells(data/'challenge.json')
    falsify(study,challenge)
    with pytest.raises(FileExistsError):falsify(study,challenge)
    valid=read_cells(data/'validation.json')
    freeze(study,valid)
    with pytest.raises(FileExistsError):freeze(study,valid)
    holdout=read_cells(data/'holdout.json')
    evaluate(study,holdout)
    with pytest.raises(FileExistsError):evaluate(study,holdout)


def test_tamper_model_and_evidence_detected(tmp_path):
    data,study=fixture(tmp_path)
    invent(read_cells(data/'training.json'),study)
    path=study/'proposal.json'
    original=path.read_text('utf-8')
    path.write_text(original.replace('learned_unary_table_v1','unsafe_python_eval'),encoding='utf-8')
    with pytest.raises(ValueError,match='checksum'):
        falsify(study,read_cells(data/'challenge.json'))
    path.write_text(original,encoding='utf-8')
    falsify(study,read_cells(data/'challenge.json'))
    freeze(study,read_cells(data/'validation.json'))
    model=study/'final_operator.json'
    model.write_text(model.read_text('utf-8').replace('learned_unary_table_v1','evil'),encoding='utf-8')
    with pytest.raises(ValueError,match='checksum'):
        evaluate(study,read_cells(data/'holdout.json'))


def test_unregistered_operator_disallowed(tmp_path):
    data,study=fixture(tmp_path)
    p=invent(read_cells(data/'training.json'),study)
    spec=dict(p['candidates'][0]['spec'])
    spec['kind']='python_eval'
    with pytest.raises(ValueError,match='unregistered'):_validate_spec(spec,p['training_sha256'])
    spec=dict(p['candidates'][0]['spec'])
    spec['mapping'][0]=100
    with pytest.raises(ValueError,match='lookup'):_validate_spec(spec,p['training_sha256'])


def test_unseen_labels_cannot_mutate_training_proposal(tmp_path):
    a,study=fixture(tmp_path)
    p=invent(read_cells(a/'training.json'),study)
    prior=(study/'proposal.json').read_bytes()
    unseen=a/'holdout.json'
    rows=json.loads(unseen.read_text('utf-8'))
    rows[0][2]=(rows[0][2]+1)%10
    unseen.write_text(json.dumps(rows),encoding='utf-8')
    assert (study/'proposal.json').read_bytes()==prior
    falsify(study,read_cells(a/'challenge.json'))
    freeze(study,read_cells(a/'validation.json'))
    # holdout changed but never used before this evaluation
    evaluation=evaluate(study,read_cells(unseen))
    assert evaluation['status']=='EVALUATED' and evaluation['holdout_errors']==1


def test_deterministic_replay(tmp_path):
    a,w=fixture(tmp_path/'first')
    a2,w2=fixture(tmp_path/'second')
    result1=stages(a,w)
    result2=stages(a2,w2)
    assert result1==result2
    for filename in ('proposal.json','falsification.json','freeze.json','evaluation.json'):
        assert (w/filename).read_bytes()==(w2/filename).read_bytes()


def test_diverse_feature_grammars_and_coverage(tmp_path):
    data,study=fixture(tmp_path)
    p=invent(read_cells(data/'training.json'),study)
    assert p['evaluated_features']==len(_features())>=10
    for item in p['candidates']:
        spec=item['spec']
        assert all(x is None or 0<=x<=9 for x in spec['mapping'])
        assert item['training_errors']==0
        assert spec['kind']=='learned_unary_table_v1'
        _validate_spec(spec,p['training_sha256'])


def test_task_setter_disjoint_all_pairs(tmp_path):
    d,s=fixture(tmp_path)
    sets=[set(read_cells(d/(k+'.json')).pairs) for k in ('training','challenge','validation','holdout')]
    assert [len(v) for v in sets]==[55,15,10,20]
    assert len(set.union(*sets))==100
    assert sum(len(v) for v in sets)==100
    with pytest.raises(FileExistsError):create_synthetic_task(d,family='random_null',seed=42)
    with pytest.raises(ValueError):create_synthetic_task(tmp_path/'invalid',family='python_code',seed=1)


def test_revise_consumes_challenge_and_requires_new_independent_gates(tmp_path):
    task,study=fixture(tmp_path,family='cubic_product',seed=3722)
    training=read_cells(task/'training.json'); challenge=read_cells(task/'challenge.json')
    invent(training,study);falsify(study,challenge)
    updated=propose_revision(study,training,challenge,tmp_path/'revision')
    assert updated['revision_provenance']['combined_training_count']==70
    assert updated['revision_provenance']['status']=='PROPOSED_NOT_VALIDATED'
    with pytest.raises(ValueError,match='leak'):
        falsify(tmp_path/'revision',challenge)
    # Correct scientific conduct: this proposal is NOT scored on the old holdout.
    assert not (tmp_path/'revision'/'evaluation.json').exists()
    with pytest.raises(FileExistsError):propose_revision(study,training,challenge,tmp_path/'revision')


def test_revise_refuses_forged_challenge_input(tmp_path):
    task,study=fixture(tmp_path)
    t=read_cells(task/'training.json');c=read_cells(task/'challenge.json')
    invent(t,study);falsify(study,c)
    wrong=read_cells(task/'holdout.json')
    with pytest.raises(ValueError,match='match'):
        propose_revision(study,t,wrong,tmp_path/'wrong')


def test_exhaustive_finite_domain_certificate(tmp_path):
    data,study=fixture(tmp_path,'cubic_sum',3722)
    _,_,selected,_=stages(data,study)
    cert=selected['finite_domain_certificate']
    assert cert['exhaustive_cells']==100
    assert cert['vector_scalar_agreement'] is True
    assert cert['commutative_on_finite_domain'] is True
    assert cert['not_a_general_math_theorem'] is True
    assert len(cert['table_sha256'])==64


def test_finite_domain_certificate_rejects_unknown_values(tmp_path):
    data,study=fixture(tmp_path,'cubic_product',3722)
    p=invent(read_cells(data/'training.json'),study)
    incomplete=[v for v in p['candidates'] if not v['coverage_complete']]
    if incomplete:
        with pytest.raises(ValueError,match='incomplete'):
            finite_domain_certificate(incomplete[0]['spec'],p['training_sha256'])


def test_revision_after_freeze_is_prohibited(tmp_path):
    task,study=fixture(tmp_path)
    t=read_cells(task/'training.json');c=read_cells(task/'challenge.json')
    invent(t,study);falsify(study,c);freeze(study,read_cells(task/'validation.json'))
    with pytest.raises(ValueError,match='precede'):
        propose_revision(study,t,c,tmp_path/'late_revision')
