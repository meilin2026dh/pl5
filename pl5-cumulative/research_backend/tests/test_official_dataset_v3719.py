"""Phase III source audit and timing-evidence adversarial tests."""
from __future__ import annotations
import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pytest

from pailie5.official_dataset_v3719 import audited_walk_forward, inspect_sources
from pailie5.prospective_validation_v3719 import register, seal, save_new
from pailie5.research_validation_v3719 import Protocol
from pailie5.timestamp_evidence_v3719 import make_request, verify_response

FIXTURES=Path(__file__).resolve().parents[2]/'data'/'official_transcriptions_v3719'
A=FIXTURES/'jiangsu_transcribed.csv'
B=FIXTURES/'gansu_transcribed.csv'
JS='https://www.js-lottery.com/Chart/p5Number'
GS='https://www.gstc.org.cn/wanfa/pl5_history'


def quality(a=A,b=B,**options):
    return inspect_sources(a,b,primary_url=JS,witness_url=GS,**options)


def test_source_transcriptions_have_expected_provenance():
    p=json.loads((FIXTURES/'PROVENANCE.json').read_text())
    assert p['source_html_bytes_saved'] is False
    assert p['site_identity_cryptographically_authenticated'] is False
    assert p['sources']['primary']['row_count']==51
    assert p['sources']['witness']['row_count']==20


def test_crosscheck_20_overlap_no_conflict():
    q=quality(min_overlap=20,require_consecutive=True)
    assert q['primary_count']==51
    assert q['witness_count']==20
    assert q['overlap_verified_count']==20
    assert q['primary_not_crosschecked_count']==31
    assert q['overlap_verified_issues'][0]=='26275'
    assert q['overlap_verified_issues'][-1]=='26294'
    assert q['raw_page_html_preserved'] is False


def test_different_paths_same_publisher_rejected():
    with pytest.raises(ValueError,match='publisher hosts'):
        inspect_sources(A,B,primary_url=JS,witness_url='https://api.js-lottery.com/historical')


def test_invalid_source_https_credentials_rejected():
    with pytest.raises(ValueError,match='HTTPS'):
        inspect_sources(A,B,primary_url='http://www.js-lottery.com',witness_url=GS)
    with pytest.raises(ValueError,match='HTTPS'):
        inspect_sources(A,B,primary_url='https://a:b@js-lottery.com',witness_url=GS)


def test_too_high_min_overlap_rejected():
    with pytest.raises(ValueError,match='insufficient'):
        quality(min_overlap=21)


def test_tampered_witness_result_rejected(tmp_path):
    p=tmp_path/'w.csv'
    p.write_text(B.read_text().replace('26294,32938','26294,32939'),encoding='utf-8')
    with pytest.raises(ValueError,match='conflicting'):
        quality(b=p)


def test_missing_issue_rejected_if_strict_consecutive(tmp_path):
    p=tmp_path/'p.csv'
    p.write_text(A.read_text().replace('26250,98581\n',''),encoding='utf-8')
    with pytest.raises(ValueError,match='gaps'):
        quality(a=p,require_consecutive=True)


def test_retrospective_only_sample_crosschecked_test_window():
    result=audited_walk_forward(A,B,primary_url=JS,witness_url=GS,
                               protocol=Protocol(warmup=40,test_size=11,top_k=100,methods=('random','positional')))
    e=result['experiment']
    assert e['test_count']==11
    assert e['first_test_issue']=='26284'
    assert e['last_test_issue']=='26294'
    assert result['evaluation_issues_all_crosschecked'] is True
    assert result['predictive_advantage']=='NOT_ESTABLISHED'
    assert e['prospective_precommitment_verified'] is False


def test_unverified_test_window_blocks_by_default():
    with pytest.raises(ValueError,match='not all crosschecked'):
        audited_walk_forward(A,B,primary_url=JS,witness_url=GS,
                             protocol=Protocol(warmup=30,test_size=30,methods=('random',)))


def test_opt_out_flag_keeps_unverified_test_marked():
    r=audited_walk_forward(A,B,primary_url=JS,witness_url=GS,
                           protocol=Protocol(warmup=30,test_size=30,methods=('random',)),
                           strict_test_crosscheck=False)
    assert r['evaluation_issues_all_crosschecked'] is False
    assert '26274' in r['evaluation_unverified_issues']


def test_full_domain_never_claimed_verified():
    r=quality()
    assert r['evidence_grade'] != 'INDEPENDENTLY_AUTHENTICATED_OFFICIAL'
    assert len(r['primary_not_crosschecked_issues'])==31


def test_timestamp_query_only_does_not_look_like_receipt(tmp_path):
    registration=register(primary=A,witness=B,primary_url=JS,witness_url=GS,
                          target_issue='26295',study_id='phase3-test',
                          protocol=Protocol(methods=('random',)))
    packet=seal(registration,A,B)
    file=tmp_path/'seal.json'
    save_new(file,packet)
    query=tmp_path/'seal.tsq'
    response=make_request(file,query)
    assert query.is_file() and query.stat().st_size>0
    assert response['tsa_response_received'] is False
    assert response['independent_timestamp_verified'] is False
    with pytest.raises(FileExistsError):make_request(file,query)


def test_timestamp_verify_does_not_accept_nonreply(tmp_path):
    registration=register(primary=A,witness=B,primary_url=JS,witness_url=GS,
                          target_issue='26295',study_id='phase3-test',
                          protocol=Protocol(methods=('random',)))
    packet=seal(registration,A,B)
    file=tmp_path/'seal.json'
    save_new(file,packet)
    reply=tmp_path/'faked.tsr'; reply.write_bytes(b'not an RFC3161 timestamp')
    ca=tmp_path/'faked.pem';ca.write_text('NOT A CERTIFICATE')
    with pytest.raises(ValueError,match='FAILED'):
        verify_response(file,reply,ca)


def test_restored_official_csv_bytes_match_original_upload_manifest():
    expected = {
        'jiangsu_transcribed.csv': (625, '6962260131f6f78072bb4b0ec95514ff8ec764e1d3a2048a275e06a24644b00e'),
        'gansu_transcribed.csv': (253, 'ca0c2ef7ff02dedc8d467a0ae1c829683339f7831911b520694cb6af7df9da26'),
    }
    for name, (size, hexdigest) in expected.items():
        original = (FIXTURES / name).read_bytes()
        assert len(original) == size
        assert sha256(original).hexdigest() == hexdigest
    provenance = json.loads((FIXTURES / 'PROVENANCE.json').read_text('utf-8'))
    assert provenance['restoration']['csvs_match_original_manifest'] is True
    assert provenance['original_provenance']['byte_exact_recovered'] is False
    assert provenance['source_html_bytes_saved'] is False
    assert provenance['site_identity_cryptographically_authenticated'] is False
