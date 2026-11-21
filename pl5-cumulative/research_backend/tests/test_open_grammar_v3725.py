"""V3.7.25 research-only safety, correctness and leakage tests."""
import json
import os
from pathlib import Path
import numpy as np
import pytest

from pailie5.structure_search_v372 import CellDataset
from pailie5.open_grammar_v3725 import (
    _solve_ring, _features, _stage_names,fit,freeze,evaluate,commit_holdout,
    program_table,
)
from research_open_grammar_v3725 import prepare,solve,grade


def _dataset(fn, seed=42, tamper_train=False):
    a,b=np.indices((10,10),dtype=np.int64)
    y=fn(a,b).astype(np.int64).reshape(100)%10
    ix=np.random.default_rng(seed).permutation(100)
    if tamper_train:y[ix[0]]=(y[ix[0]]+1)%10
    return [CellDataset(tuple((int(k//10),int(k%10),int(y[k])) for k in sub))
            for sub in (ix[:48],ix[48:64],ix[64:])]


@pytest.mark.parametrize('prime_case',[0,1,2,3,4])
def test_mod10_crt_solver_consistent(prime_case):
    rng=np.random.default_rng(2525+prime_case)
    a=rng.integers(0,10,size=(48,18),dtype=np.int64)
    c=rng.integers(0,10,size=18,dtype=np.int64)
    ans=_solve_ring(a,(a@c)%10)
    assert ans is not None and np.array_equal((a@ans)%10,(a@c)%10)


def test_ring_inconsistent_and_noninvertible():
    a=np.array([[2],[2]],dtype=np.int64)
    assert _solve_ring(a,np.array([1,1])) is None
    assert _solve_ring(a,np.array([0,2])) is None
    assert _solve_ring(a,np.array([4,4])) is not None


@pytest.mark.parametrize('task',["cubic","ltgate","parity","power"])
def test_known_synthetic_expressions(task,tmp_path):
    a,b=np.indices((10,10),dtype=np.int64)
    formula={
       'cubic':lambda a,b:(a*a*b+b*b+3)%10,
       'ltgate':lambda a,b:np.where(a<b,a*b+3,np.bitwise_xor(a,b)+3)%10,
       'parity':lambda a,b:np.where((a%2)==(b%2),a*b+3,np.bitwise_xor(a,b)+3)%10,
       'power':lambda a,b:(a**3+b**3+3)%10,
    }[task]
    tr,va,ho=_dataset(formula,seed=2026)
    nonce='qualified-private-nonce-very-long'
    rec=fit(tr,tmp_path,holdout_digest=commit_holdout(ho,nonce))
    assert rec['candidate_evaluations']==4
    fr=freeze(tmp_path,va)
    assert fr['status']=='FROZEN'
    ev=evaluate(tmp_path,ho,nonce=nonce)
    assert ev['test_errors']==0
    assert ev['lottery_predictive_advantage']=='NOT_ESTABLISHED'


def test_reject_random_noise(tmp_path):
    y=np.random.default_rng(2026).integers(0,10,(10,10))
    tr,va,ho=_dataset(lambda a,b:y)
    fit(tr,tmp_path)
    assert freeze(tmp_path,va)['status']=='ABSTAIN'
    assert evaluate(tmp_path,ho)['status']=='ABSTAIN'


def test_bounded_dsl_no_injection():
    base={'syntax':'mod10_sparse_basis','stage':'parity_gate',
          'features':['a'],'coefficients':[1]}
    assert len(program_table(base))==100
    with pytest.raises(ValueError):program_table({**base,'features':['__import__("os").system("echo BAD")']})
    with pytest.raises(ValueError):program_table({**base,'coefficients':[1.0]})
    with pytest.raises(ValueError):program_table({**base,'hidden':42})
    assert len(_features())==len(_stage_names()['parity_gate'])


def test_partition_overlap_rejected(tmp_path):
    tr,va,ho=_dataset(lambda a,b:(a+b)%10)
    fit(tr,tmp_path)
    with pytest.raises(ValueError,match='overlap'):
        freeze(tmp_path,tr)
    freeze(tmp_path,va)
    with pytest.raises(ValueError,match='overlap'):
        evaluate(tmp_path,tr)


def test_commitment_mismatch_and_no_overwrite(tmp_path):
    tr,va,ho=_dataset(lambda a,b:(a+b)%10)
    nonce='qualified-private-nonce-very-long'
    fit(tr,tmp_path,holdout_digest=commit_holdout(ho,nonce))
    with pytest.raises(FileExistsError):fit(tr,tmp_path,holdout_digest=commit_holdout(ho,nonce))
    freeze(tmp_path,va)
    with pytest.raises(ValueError,match='commitment'):
        evaluate(tmp_path,ho,nonce='wrong-nonce-here-very-long')
    evaluate(tmp_path,ho,nonce=nonce)
    with pytest.raises(FileExistsError):evaluate(tmp_path,ho,nonce=nonce)


def _challenge_json(path, tamper_train=False):
    tr,va,ho=_dataset(lambda a,b:(a*a*b+b*b+3)%10,tamper_train=tamper_train)
    body={'task_id':'external_example_001','source_description':'self-reported synthetic fixture',
          'train':[list(row) for row in tr.rows],
          'validation':[list(row) for row in va.rows],
          'holdout':[list(row) for row in ho.rows]}
    path.write_text(json.dumps(body),encoding='utf-8')


def test_public_private_issuer_split(tmp_path):
    challenge=tmp_path/'challenge.json';_challenge_json(challenge)
    root=tmp_path/'public';priv=tmp_path/'private';result=tmp_path/'solver'
    setup=prepare(challenge,root,priv)
    assert setup['external_blind_verified'] is False
    pub=root/'public_challenge.json'; private=priv/'private_challenge.json'
    assert 'holdout' not in json.loads(pub.read_text())
    assert 'nonce' not in pub.read_text()
    if os.name=='posix':assert (private.stat().st_mode&0o777)==0o600
    frozen=solve(pub,result)
    assert frozen['status']=='FROZEN'
    ev=grade(pub,private,result)
    assert ev['errors']==0 and ev['digest_verified']
    with pytest.raises(FileExistsError):grade(pub,private,result)


def test_tamper_private_rejected(tmp_path):
    challenge=tmp_path/'challenge.json';_challenge_json(challenge)
    root=tmp_path/'public';priv=tmp_path/'private';result=tmp_path/'solver'
    prepare(challenge,root,priv)
    pub=root/'public_challenge.json'; private=priv/'private_challenge.json'
    solve(pub,result)
    data=json.loads(private.read_text());data['holdout'][0][2]=(data['holdout'][0][2]+1)%10
    private.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='commitment'):
        grade(pub,private,result)


def test_tamper_public_rejected(tmp_path):
    challenge=tmp_path/'challenge.json';_challenge_json(challenge)
    root=tmp_path/'public';priv=tmp_path/'private'
    prepare(challenge,root,priv)
    pub=root/'public_challenge.json';data=json.loads(pub.read_text())
    data['train'][0][2]=(data['train'][0][2]+1)%10
    pub.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='modified'):
        solve(pub,tmp_path/'solver')


def test_challenge_duplicate_rejected(tmp_path):
    challenge=tmp_path/'challenge.json';_challenge_json(challenge)
    data=json.loads(challenge.read_text());data['holdout'].append(data['train'][0]);challenge.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='overlap'):
        prepare(challenge,tmp_path/'public',tmp_path/'private')


def test_corrupted_training_abstains(tmp_path):
    tr,va,ho=_dataset(lambda a,b:(a*a*b+b*b+2)%10,tamper_train=True)
    fit(tr,tmp_path)
    assert freeze(tmp_path,va)['status']=='ABSTAIN'
