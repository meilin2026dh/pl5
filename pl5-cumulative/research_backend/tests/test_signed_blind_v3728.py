"""V3.7.28 tests: signatures, code hashes, frozen evidence, replay guards."""
import json
import shutil
from pathlib import Path

import pytest

from benchmark_hard_budget_v3727 import SEEDS, task
from research_open_grammar_v3725 import prepare
from research_signed_blind_v3728 import (keygen, issue, verify_issue, freeze,
    verify_freeze, settle, verify_settlement, _verify, _read, _fingerprint,
    code_inventory, _sign, ISSUER, SOLVER, _sha, _bytes)

BACKEND = Path(__file__).resolve().parents[1]


def _keys(root):
    ret={}
    for role in ('issuer','solver','grader','wrong'):
        priv=root/f'{role}.key';pub=root/f'{role}.pub'
        ret[role]=(priv,pub)
        keygen(priv,pub)
    return ret


def _challenge(root, family='equal_gate'):
    c=root/'challenge.json'
    c.write_text(json.dumps(task(family, SEEDS[0])))
    prepare(c,root/'public',root/'private')
    return root/'public/public_challenge.json',root/'private/private_challenge.json'


def _issuer(root,keys):
    pub,priv=_challenge(root)
    a=root/'issuer_attestation.json'
    issue(pub,BACKEND,*keys['issuer'],a,5000)
    return pub,priv,a


def test_generate_keys_are_distinct_and_private(tmp_path):
    keys=_keys(tmp_path)
    assert len({_fingerprint(v[1]) for v in keys.values()})==4
    with pytest.raises(FileExistsError):keygen(*keys['issuer'])
    assert (keys['issuer'][0].stat().st_mode & 0o777)==0o600
    assert b'PRIVATE KEY' in keys['issuer'][0].read_bytes()
    assert b'PRIVATE KEY' not in keys['issuer'][1].read_bytes()


def test_signature_verification_and_wrong_key(tmp_path):
    keys=_keys(tmp_path)
    pub,_,att=_issuer(tmp_path,keys)
    assert verify_issue(pub,BACKEND,att,keys['issuer'][1])['task_id']
    with pytest.raises(ValueError,match='signature'):
        verify_issue(pub,BACKEND,att,keys['wrong'][1])
    with pytest.raises(ValueError,match='issuer public/private'):
        issue(pub,BACKEND,keys['issuer'][0],keys['wrong'][1],tmp_path/'bad.json',3000)


def test_changed_signed_metadata_is_detected(tmp_path):
    keys=_keys(tmp_path);pub,_,att=_issuer(tmp_path,keys)
    d=_read(att);d['payload']['allowed_budget_ms_per_model']=7000
    att.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='signature'):
        verify_issue(pub,BACKEND,att,keys['issuer'][1])


def test_unsigned_public_modification_is_rejected(tmp_path):
    keys=_keys(tmp_path);pub,_,att=_issuer(tmp_path,keys)
    d=_read(pub);d['train'][0][2]=(d['train'][0][2]+1)%10
    pub.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='modified'):
        verify_issue(pub,BACKEND,att,keys['issuer'][1])


def test_code_hash_is_pinned_and_readme_not_in_scope(tmp_path):
    keys=_keys(tmp_path);pub,_,att=_issuer(tmp_path,keys)
    a=verify_issue(pub,BACKEND,att,keys['issuer'][1])
    assert a['model_source_file_count']>=100
    assert a['model_source_tree_sha256']==code_inventory(BACKEND)['sha256']
    scratch=tmp_path/'shadow';scratch.mkdir()
    for sub in ('pailie5','autoresearch'):
        shutil.copytree(BACKEND/sub,scratch/sub,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for src in ('pyproject.toml','research_signed_blind_v3728.py','research_hard_budget_v3727.py',
                'research_open_grammar_v3725.py','research_external_challenge_v3726.py',
                'benchmark_gate_induction_v3726.py'):
        shutil.copyfile(BACKEND/src,scratch/src)
    assert code_inventory(scratch)['sha256']==a['model_source_tree_sha256']
    (scratch/'pailie5/__init__.py').write_text('# tampered source')
    with pytest.raises(ValueError,match='source-tree'):
        verify_issue(pub,scratch,att,keys['issuer'][1])


def test_strict_budget_validation_and_nonoverwriting(tmp_path):
    keys=_keys(tmp_path);pub,_,att=_issuer(tmp_path,keys)
    with pytest.raises(FileExistsError):issue(pub,BACKEND,*keys['issuer'],att,5000)
    with pytest.raises(ValueError):issue(pub,BACKEND,*keys['issuer'],tmp_path/'bad',0)


def test_cannot_solve_with_wrong_issuer_or_solver_keys(tmp_path):
    keys=_keys(tmp_path);pub,_,att=_issuer(tmp_path,keys)
    with pytest.raises(ValueError,match='signature'):
        freeze(pub,BACKEND,att,keys['wrong'][1],*keys['solver'],tmp_path/'no1')
    with pytest.raises(ValueError,match='solver public/private'):
        freeze(pub,BACKEND,att,keys['issuer'][1],keys['solver'][0],keys['wrong'][1],tmp_path/'no2')
    assert not (tmp_path/'no1').exists() and not (tmp_path/'no2').exists()


def test_full_signed_rehearsal_and_replay_block(tmp_path):
    keys=_keys(tmp_path);pub,priv,att=_issuer(tmp_path,keys)
    out=tmp_path/'solver'
    ret=freeze(pub,BACKEND,att,keys['issuer'][1],*keys['solver'],out)
    assert set(ret['statuses'])=={'v3725_ring','v3726_gate'}
    assert verify_freeze(pub,BACKEND,att,keys['issuer'][1],keys['solver'][1],out)['task_id']
    with pytest.raises(ValueError,match='signature'):
        verify_freeze(pub,BACKEND,att,keys['issuer'][1],keys['wrong'][1],out)
    result=settle(pub,priv,BACKEND,att,keys['issuer'][1],keys['solver'][1],*keys['grader'],out)
    assert result['authentic_signatures_verified'] is True
    assert result['issuer_independence_verified'] is False
    final=verify_settlement(pub,BACKEND,att,keys['issuer'][1],keys['solver'][1],keys['grader'][1],out)
    assert final['signed_evidence_verified'] is True
    assert not final['actual_external_blind_study_verified']
    assert not final['third_party_clock_verified']
    with pytest.raises(FileExistsError):
        settle(pub,priv,BACKEND,att,keys['issuer'][1],keys['solver'][1],*keys['grader'],out)
    with pytest.raises(FileExistsError):
        freeze(pub,BACKEND,att,keys['issuer'][1],*keys['solver'],out)
    score=_read(out/'score.json')
    assert score['arms']['v3726_gate']['holdout_errors']==0
    # Damage the signed grade, and the auditor must refuse it.
    path=out/'score.json';data=path.read_bytes()+b'\n'
    path.write_bytes(data)
    with pytest.raises(ValueError,match='grader receipt mismatch'):
        verify_settlement(pub,BACKEND,att,keys['issuer'][1],keys['solver'][1],keys['grader'][1],out)


def test_receipt_canonicalization_is_repeatable(tmp_path):
    keys=_keys(tmp_path)
    p={'a':1,'b':['x','y']}
    assert _sha(_bytes(p))==_sha(_bytes({'b':['x','y'],'a':1}))
    f=tmp_path/'sig.json';f.write_text(json.dumps(_sign(p,keys['issuer'][0],ISSUER)))
    assert _verify(f,keys['issuer'][1],ISSUER)==p
    with pytest.raises(ValueError):_verify(f,keys['issuer'][1],SOLVER)
