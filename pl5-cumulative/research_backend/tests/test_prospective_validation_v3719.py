"""Phase II adversarial integrity, no-lookahead and two-source settlement checks."""
from __future__ import annotations
import copy
import csv
import json

import numpy as np
import pytest

from pailie5.prospective_validation_v3719 import (
    checked_document, read_draw_csv, read_evidence, reconcile, register, save_new,
    seal, settle, verify_document, verify_seal, verify_settlement,
)
from pailie5.research_validation_v3719 import Protocol


def fixture_sources(tmp_path, n=43, *, outcome=False):
    primary=tmp_path/'primary.csv'
    witness=tmp_path/'witness.csv'
    base=[(str(26200+i),f'{(i*721+39)%100000:05d}') for i in range(n)]
    if outcome:
        base.append((str(26200+n), '00000'))
    def write(path, rows, issue_header='issue', newline='\n'):
        # distinct raw files, same parsed data
        with path.open('w',encoding='utf-8',newline='') as f:
            f.write(f'{issue_header},number{newline}')
            for x,y in rows:f.write(f'{x},{y}{newline}')
    write(primary,base)
    write(witness,base,'period','\r\n')
    return primary,witness,base


def prereg(tmp_path, *, n=43, target=None, methods=('random','positional')):
    a,b,rows=fixture_sources(tmp_path,n=n)
    r=register(primary=a,witness=b,primary_url='https://official.test/draws',
               witness_url='https://other.test/draws',
               target_issue=target or str(26200+n),study_id='pre-registered-1',
               protocol=Protocol(warmup=40,test_size=1,top_k=100,methods=methods))
    return a,b,rows,r


def cheap_predictor(past,method,p,index):
    assert len(past)==index
    return np.arange(p.top_k,dtype=np.int32) if method=='random' else np.arange(1,p.top_k+1,dtype=np.int32)


def test_crosscheck_matching_real_rows_but_not_authentication(tmp_path):
    a,b,rows=fixture_sources(tmp_path)
    cross=reconcile(a,b,min_overlap=40)
    assert cross['matched_count']==43
    assert cross['unchecked_primary_count']==0
    assert cross['source_authentication']=='NOT_INDEPENDENTLY_AUTHENTICATED'
    assert read_draw_csv(a)[0][-1].number==rows[-1][1]


def test_crosscheck_rejects_disagreement_even_one(tmp_path):
    a,b,rows=fixture_sources(tmp_path)
    w=b.read_text().replace(rows[7][1],'99999',1)
    b.write_text(w)
    with pytest.raises(ValueError,match='conflicting'):
        reconcile(a,b)


def test_crosscheck_rejects_identical_file_bytes(tmp_path):
    a,b,_=fixture_sources(tmp_path)
    b.write_bytes(a.read_bytes())
    with pytest.raises(ValueError,match='byte-identical'):
        reconcile(a,b)


def test_crosscheck_rejects_same_file(tmp_path):
    a,b,_=fixture_sources(tmp_path)
    with pytest.raises(ValueError,match='distinct'):
        reconcile(a,a)


def test_source_requires_strict_order_no_duplicate_issue(tmp_path):
    a,b,_=fixture_sources(tmp_path)
    a.write_text('issue,number\n26202,00000\n26201,00001\n')
    with pytest.raises(ValueError):read_draw_csv(a)
    a.write_text('issue,number\n26201,00000\n26201,00001\n')
    with pytest.raises(ValueError):read_draw_csv(a)


def test_source_preserves_zero_leading_and_rejects_fullwidth(tmp_path):
    a,b,_=fixture_sources(tmp_path)
    a.write_text('issue,number\n26201,00001\n')
    assert read_draw_csv(a)[0][0].number=='00001'
    a.write_text('issue,number\n26201,１２３４５\n')
    with pytest.raises(ValueError):read_draw_csv(a)


def test_registration_rejects_target_already_drawn(tmp_path):
    a,b,rows=fixture_sources(tmp_path)
    with pytest.raises(ValueError,match='follow'):
        register(primary=a,witness=b,primary_url='https://a',witness_url='https://b',
                 target_issue=rows[-1][0],study_id='x',protocol=Protocol())


def test_registration_requires_two_urls_and_valid_study_id(tmp_path):
    a,b,_=fixture_sources(tmp_path)
    with pytest.raises(ValueError,match='HTTPS'):
        register(primary=a,witness=b,primary_url='file:///tmp/a',witness_url='https://b',
                 target_issue='26243',study_id='x',protocol=Protocol())
    with pytest.raises(ValueError,match='study id'):
        register(primary=a,witness=b,primary_url='https://a',witness_url='https://b',
                 target_issue='26243',study_id='../x',protocol=Protocol())


def test_seal_candidates_are_frozen_sorted_and_replayable(tmp_path):
    a,b,rows,r=prereg(tmp_path)
    p=seal(r,a,b,predictor=cheap_predictor)
    verify_seal(r,p)
    assert len(p['candidates'])==2
    assert p['candidates']['random']['numbers'][0]=='00000'
    assert len(p['candidates']['positional']['numbers'])==100
    assert p['attestation_status']=='LOCAL_HASH_ONLY_NO_INDEPENDENT_TIMESTAMP'
    assert p['prospective_precommitment_verified'] is False
    assert p['target_issue']==str(26200+len(rows))


def test_changed_training_source_blocks_seal(tmp_path):
    a,b,rows,r=prereg(tmp_path)
    # alter both sources in lockstep: no two-source disagreement, but frozen snapshot differs
    for path in (a,b):
        path.write_text(path.read_text().replace(rows[0][1],'99999',1))
    with pytest.raises(ValueError,match='source snapshots changed'):
        seal(r,a,b,predictor=cheap_predictor)


def test_seal_rejects_bad_candidate_budget(tmp_path):
    a,b,rows,r=prereg(tmp_path)
    with pytest.raises(ValueError,match='frozen integer budget'):
        seal(r,a,b,predictor=lambda *args:np.arange(99))


def test_seal_rejects_duplicate_numbers(tmp_path):
    a,b,rows,r=prereg(tmp_path)
    with pytest.raises(ValueError,match='unique'):
        seal(r,a,b,predictor=lambda *args:np.zeros(100,dtype=int))


def test_registration_digest_tamper_is_caught(tmp_path):
    a,b,rows,r=prereg(tmp_path)
    changed=copy.deepcopy(r)
    changed['target_issue']='99999'
    with pytest.raises(ValueError,match='checksum'):
        seal(changed,a,b,predictor=cheap_predictor)


def test_packet_tamper_is_caught(tmp_path):
    a,b,rows,r=prereg(tmp_path)
    packet=seal(r,a,b,predictor=cheap_predictor)
    fake=copy.deepcopy(packet)
    fake['candidates']['random']['numbers'][0]='12345'
    with pytest.raises(ValueError,match='checksum'):
        verify_seal(r,fake)


def test_prospective_settlement_only_after_target_is_available_and_crosschecked(tmp_path):
    a,b,rows,r=prereg(tmp_path)
    packet=seal(r,a,b,predictor=cheap_predictor)
    with pytest.raises(ValueError,match='target issue absent'):
        settle(r,packet,a,b)
    a2,b2,_=fixture_sources(tmp_path,outcome=True)
    result=settle(r,packet,a2,b2)
    verify_settlement(r,packet,result)
    assert result['outcome']=='00000'
    assert result['results']['random']['hit'] is True
    assert result['results']['positional']['hit'] is False
    assert result['predictive_advantage']=='NOT_ESTABLISHED'
    assert result['evidence_level']=='LOCAL_PROSPECTIVE_WORKFLOW_NOT_EXTERNALLY_TIMESTAMPED'
    assert result['fair_baseline_hit_probability_per_method']==0.001


def test_settlement_rejects_cross_source_target_conflict(tmp_path):
    a,b,rows,r=prereg(tmp_path)
    packet=seal(r,a,b,predictor=cheap_predictor)
    a,b,rows2=fixture_sources(tmp_path,outcome=True)
    b.write_text(b.read_text().replace('00000','99999'))
    with pytest.raises(ValueError,match='conflicting'):
        settle(r,packet,a,b)


def test_settlement_rejects_changed_prefix(tmp_path):
    a,b,rows,r=prereg(tmp_path)
    packet=seal(r,a,b,predictor=cheap_predictor)
    a,b,_=fixture_sources(tmp_path,outcome=True)
    for path in (a,b):
        path.write_text(path.read_text().replace(rows[0][1],'12345',1))
    with pytest.raises(ValueError,match='prefix modified'):
        settle(r,packet,a,b)


def test_exclusive_file_creation_and_verify_reload(tmp_path):
    a,b,rows,r=prereg(tmp_path)
    reg_path=tmp_path/'registration.json'
    save_new(reg_path,r)
    with pytest.raises(FileExistsError):save_new(reg_path,r)
    assert read_evidence(reg_path,'registration')==r
    packet=seal(r,a,b,predictor=cheap_predictor)
    packet_path=tmp_path/'seal.json';save_new(packet_path,packet)
    verify_seal(read_evidence(reg_path,'registration'),read_evidence(packet_path,'seal'))


def test_seal_same_input_same_candidate_hash(tmp_path):
    a,b,rows,r=prereg(tmp_path)
    x=seal(r,a,b,predictor=cheap_predictor)
    y=seal(r,a,b,predictor=cheap_predictor)
    assert [v['candidate_sha256'] for v in x['candidates'].values()] == [v['candidate_sha256'] for v in y['candidates'].values()]


def test_recomputed_checksum_cannot_relabel_candidate_sha(tmp_path):
    a,b,rows,r=prereg(tmp_path)
    p=seal(r,a,b,predictor=cheap_predictor)
    tampered=copy.deepcopy(p)
    tampered['candidates']['random']['candidate_sha256']='0'*64
    tampered=checked_document({k:v for k,v in tampered.items() if k!='document_sha256'})
    with pytest.raises(ValueError,match='candidate bytes digest mismatch'):
        verify_seal(r,tampered)
