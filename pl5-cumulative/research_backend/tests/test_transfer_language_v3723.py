"""V3723 finite-program transfer contract: strict separation, integrity and abstention."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest

from pailie5.language_evolution_v3722 import create_synthetic_task,invent,falsify,freeze,evaluate,_write_new
from pailie5.math_discovery_v3720 import read_cells
from pailie5.structure_search_v372 import CellDataset
from pailie5.transfer_language_v3723 import (
    certify_source_bank,compress_lookup,fit_target,freeze_target,evaluate_target,
    public_holdout_digest,_read_checked,_bank,_outputs,VERSION,
)

@pytest.fixture(scope='module')
def source_bank(tmp_path_factory):
    root=tmp_path_factory.mktemp('v3723_sources')
    studies=[]
    for i,family in enumerate(('cubic_sum','step_sum','square_difference','parity_difference')):
        d=root/f'data_{i}';s=root/f'study_{i}'
        create_synthetic_task(d,family=family,seed=3722)
        invent(read_cells(d/'training.json'),s)
        falsify(s,read_cells(d/'challenge.json'))
        assert freeze(s,read_cells(d/'validation.json'))['status']=='FROZEN'
        assert evaluate(s,read_cells(d/'holdout.json'))['holdout_errors']==0
        studies.append(s)
    bank_path=root/'bank.json'
    bank=certify_source_bank(studies,bank_path)
    return root,studies,bank_path,bank


def make_target(source_bank,root,*,kind='positive'):
    _,_,bank_path,bank=source_bank
    a,b=np.indices((10,10))
    if kind=='positive':
        from pailie5.transfer_language_v3723 import _table
        table=_table(bank['templates'][0],3,4)
    elif kind=='null':
        table=np.random.default_rng(389).integers(0,10,(10,10))
    else:
        table=(a*a*b+2*a+b*b)%10
    perm=np.random.default_rng(3723).permutation(100)
    parts={}
    start=0
    for name,n in [('train',24),('validation',20),('holdout',56)]:
        ids=perm[start:start+n];start+=n
        parts[name]=CellDataset(tuple((int(i//10),int(i%10),int(table.flat[i])) for i in ids))
    return parts


def test_certified_source_bank_and_compression(source_bank):
    root,studies,path,bank=source_bank
    assert len(bank['templates'])==4
    assert {p['kind'] for p in bank['templates']} == {'poly3','poly2','step','parity'}
    assert all(p['mdl_proxy_bits']<p['lookup_proxy_bits'] for p in bank['templates'])
    for p in bank['templates']:
        assert p['finite_domain_only'] and len(p['finite_table_sha256'])==64
    with pytest.raises(FileExistsError):certify_source_bank(studies,path)


def test_uncertified_source_rejected(source_bank,tmp_path):
    _,studies,_,_=source_bank
    with pytest.raises(ValueError,match='source not independently certified'):
        certify_source_bank([studies[0],studies[0]],tmp_path/'duplicate.json')
    incomplete=tmp_path/'unverified_source';incomplete.mkdir()
    with pytest.raises(FileNotFoundError):certify_source_bank([incomplete],tmp_path/'bad.json')


def test_transfer_with_precommit_and_one_shot(source_bank,tmp_path):
    parts=make_target(source_bank,tmp_path)
    bank_path=source_bank[2];study=tmp_path/'fit'
    nonce='random-secret-nonce-for-reveal-after-freeze'
    digest=public_holdout_digest(parts['holdout'],nonce)
    p=fit_target(parts['train'],bank_path,study,candidate_budget=4,holdout_commitment=digest)
    assert p['test_labels_used'] is False and p['precommitted_holdout_digest']==digest
    frozen=freeze_target(study,bank_path,parts['validation'])
    assert frozen['status']=='FROZEN'
    with pytest.raises(ValueError,match='missing nonce'):
        evaluate_target(study,bank_path,parts['holdout'])
    res=evaluate_target(study,bank_path,parts['holdout'],reveal_nonce=nonce)
    assert res['status']=='EVALUATED' and res['errors']==0 and res['holdout_commitment_matched']
    with pytest.raises(FileExistsError):evaluate_target(study,bank_path,parts['holdout'],reveal_nonce=nonce)
    with pytest.raises(FileExistsError):fit_target(parts['train'],bank_path,study)
    with pytest.raises(FileExistsError):freeze_target(study,bank_path,parts['validation'])


def test_bad_holdout_reveal_rejected(source_bank,tmp_path):
    parts=make_target(source_bank,tmp_path)
    bank=source_bank[2];study=tmp_path/'one'
    nonce='random-secret-nonce-for-reveal-after-freeze'
    fit_target(parts['train'],bank,study,holdout_commitment=public_holdout_digest(parts['holdout'],nonce))
    freeze_target(study,bank,parts['validation'])
    with pytest.raises(ValueError,match='commitment mismatch'):
        evaluate_target(study,bank,parts['holdout'],reveal_nonce='incorrect-nonce-with-sufficient-entropy')
    rows=list(parts['holdout'].rows)
    a,b,y=rows[0];rows[0]=(a,b,(y+1)%10)
    with pytest.raises(ValueError,match='commitment mismatch'):
        evaluate_target(study,bank,CellDataset(tuple(rows)),reveal_nonce=nonce)
    assert not (study/'evaluation.json').exists()


def test_null_and_unseen_interaction_abstain(source_bank,tmp_path):
    for kind in ('null','interaction'):
        parts=make_target(source_bank,tmp_path,kind=kind)
        study=tmp_path/kind
        fit_target(parts['train'],source_bank[2],study)
        frozen=freeze_target(study,source_bank[2],parts['validation'])
        measured=evaluate_target(study,source_bank[2],parts['holdout'])
        assert frozen['status']=='ABSTAIN'
        assert measured['status']=='ABSTAIN' and measured['errors'] is None


def test_train_validation_holdout_disjoint(source_bank,tmp_path):
    parts=make_target(source_bank,tmp_path)
    study=tmp_path/'one'
    fit_target(parts['train'],source_bank[2],study)
    with pytest.raises(ValueError,match='overlap'):
        freeze_target(study,source_bank[2],parts['train'])
    freeze_target(study,source_bank[2],parts['validation'])
    with pytest.raises(ValueError,match='overlap'):
        evaluate_target(study,source_bank[2],parts['train'])


def test_frozen_bank_modified_detected(source_bank,tmp_path):
    parts=make_target(source_bank,tmp_path)
    bank=source_bank[2];study=tmp_path/'one'
    fit_target(parts['train'],bank,study)
    original=bank.read_bytes()
    try:
        bank.write_bytes(original.replace(b'"poly3"',b'"unsafe"',1))
        with pytest.raises(ValueError,match='checksum'):
            freeze_target(study,bank,parts['validation'])
    finally:bank.write_bytes(original)


def test_spec_rejects_unregistered_and_malformed_programs():
    x=np.array([0,1,2],dtype=np.int64)
    with pytest.raises(ValueError,match='unregistered'):_outputs({'kind':'python_eval','params':[1]},x)
    with pytest.raises(ValueError,match='invalid parameters'):_outputs({'kind':'poly1','params':[1,'2']},x)
    with pytest.raises(ValueError,match='malformed'):_outputs({'kind':'step','params':[0,2,3]},x)


def test_empty_source_and_digest_invalid(source_bank,tmp_path):
    with pytest.raises(ValueError):certify_source_bank([],tmp_path/'nobank.json')
    parts=make_target(source_bank,tmp_path)
    with pytest.raises(ValueError,match='nonce'):public_holdout_digest(parts['holdout'],'short')
    with pytest.raises(ValueError,match='commitment'):
        fit_target(parts['train'],source_bank[2],tmp_path/'study',holdout_commitment='incorrect')


def test_replay_equal(source_bank,tmp_path):
    parts=make_target(source_bank,tmp_path)
    values=[]
    for n in ('first','second'):
        study=tmp_path/n
        p=fit_target(parts['train'],source_bank[2],study)
        f=freeze_target(study,source_bank[2],parts['validation'])
        e=evaluate_target(study,source_bank[2],parts['holdout'])
        values.append([p,f,e])
    assert values[0]==values[1]


def test_compression_cannot_use_partial_source_lookup(source_bank):
    root,studies,_,_=source_bank
    p=_read_checked(studies[0]/'proposal.json','pl5-v3722-grammar-extension-1:proposal')
    spec=dict(p['candidates'][0]['spec'])
    # Validating the altered operator digest must reject unsigned mutation.
    spec['mapping']=list(spec['mapping'])
    spec['mapping'][0]=None
    with pytest.raises(ValueError):compress_lookup(spec,p['training_sha256'])
