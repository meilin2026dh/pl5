"""Fail-closed timeout protocol and mathematical task integrity tests."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import numpy as np

from research_hard_budget_v3727 import solve,grade,_validated_budget,ARMS,SCHEMA
from research_open_grammar_v3725 import prepare
from benchmark_hard_budget_v3727 import task,target,FAMILIES,SEEDS


def fixture(tmp_path,kind='equal_gate'):
    challenge=tmp_path/'challenge.json'
    challenge.write_text(json.dumps(task(kind,SEEDS[0])))
    prepare(challenge,tmp_path/'public',tmp_path/'private')
    return tmp_path/'public'/'public_challenge.json',tmp_path/'private'/'private_challenge.json'


def test_budget_validation():
    for value in (0,-2,99,60001,True,0.3,'1000'):
        with pytest.raises(ValueError):_validated_budget(value)
    assert _validated_budget(800)==800


def test_offline_model_does_not_receive_private_labels(tmp_path):
    pub,priv=fixture(tmp_path)
    data=json.loads(pub.read_text())
    assert set(data)=={'schema','task_id','train','validation','holdout_commitment',
                       'source_description_self_reported','issuer_identity_externally_verified',
                       'evaluation_grade','version','protocol_sha256'}
    assert 'nonce' not in pub.read_text() and 'holdout' not in data
    assert 'holdout' in priv.read_text()


def test_hard_deadline_uses_real_os_timeout():
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run([sys.executable,'-c','import time;time.sleep(0.3)'],timeout=0.03)


def test_full_frozen_grade_and_no_rescoring(tmp_path):
    pub,priv=fixture(tmp_path)
    result=solve(pub,tmp_path/'solver',5000)
    assert set(result['arms'])==set(ARMS)
    assert all(x['status']=='COMPLETED' for x in result['arms'].values())
    scores=grade(pub,priv,tmp_path/'solver')
    assert scores['v3726_gate']['holdout_errors']==0
    assert scores['frozen_portfolio']['budget_ms_total']==10000
    with pytest.raises(FileExistsError):grade(pub,priv,tmp_path/'solver')
    with pytest.raises(FileExistsError):solve(pub,tmp_path/'solver',5000)


def test_wrong_private_digest_rejected(tmp_path):
    pub,priv=fixture(tmp_path)
    solve(pub,tmp_path/'solver',5000)
    data=json.loads(priv.read_text())
    data['holdout'][0][2]=(data['holdout'][0][2]+1)%10
    priv.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='commitment'):grade(pub,priv,tmp_path/'solver')
    assert not (tmp_path/'solver'/'score.json').exists()


def test_invalid_public_hash_rejected_before_running(tmp_path):
    pub,priv=fixture(tmp_path)
    data=json.loads(pub.read_text())
    data['train'][0][2]=(data['train'][0][2]+1)%10
    pub.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='modified'):solve(pub,tmp_path/'solver',2000)


def test_worker_receipt_tampering_rejected(tmp_path):
    pub,priv=fixture(tmp_path)
    solve(pub,tmp_path/'solver',5000)
    fr=tmp_path/'solver'/'v3726_gate'/'freeze.json'
    data=json.loads(fr.read_text());data['status']='ABSTAIN';fr.write_text(json.dumps(data))
    with pytest.raises(ValueError):grade(pub,priv,tmp_path/'solver')
    assert not (tmp_path/'solver'/'score.json').exists()


def test_timed_out_arms_never_scored(tmp_path,monkeypatch):
    pub,priv=fixture(tmp_path)
    # Force timeout deterministically rather than assuming machine startup speed.
    def forced_timeout(*args,**kwargs):
        raise subprocess.TimeoutExpired(cmd=['test-worker'],timeout=kwargs.get('timeout',1))
    monkeypatch.setattr('research_hard_budget_v3727.subprocess.run',forced_timeout)
    result=solve(pub,tmp_path/'solver',100)
    assert all(x['status']=='TIMED_OUT' for x in result['arms'].values())
    gradebook=grade(pub,priv,tmp_path/'solver')
    for arm in ARMS:
        if result['arms'][arm]['status']=='TIMED_OUT':
            assert gradebook[arm]['status']=='TIMED_OUT'
            assert gradebook[arm]['holdout_errors'] is None
            assert not (tmp_path/'solver'/arm/'evaluation.json').exists()


def test_no_family_target_information_passes_in_public_challenge(tmp_path):
    pub,_=fixture(tmp_path,'cubic_polynomial')
    content=pub.read_text()
    assert 'cubic_polynomial' not in content
    assert 'train' in content


@pytest.mark.parametrize('family',FAMILIES)
def test_developer_fixture_labels_are_digit_domain(family):
    y=target(family,SEEDS[0])
    assert y.shape==(100,) and np.all((y>=0)&(y<10))


def test_seeded_tasks_split_without_overlap():
    for family in FAMILIES:
        r=task(family,SEEDS[0]);parts=[r[k] for k in ('train','validation','holdout')]
        assert [len(p) for p in parts]==[48,16,36]
        assert len({(a,b) for p in parts for a,b,_ in p})==100
