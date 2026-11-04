import hashlib
import io
import json
import sqlite3
from pathlib import Path
import numpy as np
import pytest
from autoresearch.formulas import (InventedAlgorithm,invent_from_text,validate_expr,vector_eval,scalar_eval,emit_review_code)
from autoresearch.verification import choose_candidate_ids,replicate_formula,walk_forward_falsify,full_audit
from autoresearch.registry_v06 import ResearchRegistry
from autoresearch.workflow_v06 import run_for_document
from autoresearch.fulltext import arxiv_id_from_metadata,read_local_document,fetch_arxiv_pdf
from autoresearch.llm_v06 import propose_with_model


def algo():
    return InventedAlgorithm({'kind':'op','op':'mod','args':[
        {'kind':'op','op':'absdiff','args':[{'kind':'metric','name':'sum'},
                                          {'kind':'metric','name':'span'}]},
        {'kind':'const','value':5}]},'constant',3,'test','derived research idea')


def test_bounded_ast_rejects_unsafe_code():
    with pytest.raises(ValueError):validate_expr({'kind':'metric','name':'__import__'})
    with pytest.raises(ValueError):validate_expr({'kind':'op','op':'eval','args':[{'kind':'const','value':2},{'kind':'const','value':3}]})
    with pytest.raises(ValueError):validate_expr({'kind':'op','op':'mod','args':[{'kind':'metric','name':'sum'},{'kind':'metric','name':'span'}]})
    with pytest.raises(ValueError):validate_expr({'kind':'const','value':0})
    nest={'kind':'metric','name':'sum'}
    for _ in range(5):nest={'kind':'op','op':'add','args':[nest,{'kind':'const','value':2}]}
    with pytest.raises(ValueError):validate_expr(nest)


def test_double_interpreter_replication_and_code_review():
    spec=algo();rep=replicate_formula(spec,sample=64)
    assert rep['matches'] and len(rep['value_sha256'])==64
    arr=vector_eval(spec.formula,ids=[0,128,99999])
    assert arr.tolist()==[scalar_eval(spec.formula,i) for i in (0,128,99999)]
    assert 'REVIEW ONLY' in emit_review_code(spec.formula)


def test_invention_deterministic_bounded():
    a=invent_from_text('sequential method change point', 'doc-001', limit=5)
    b=invent_from_text('sequential method change point', 'doc-001', limit=5)
    assert [s.fingerprint() for s in a]==[s.fingerprint() for s in b]
    assert len(set(s.fingerprint() for s in a))==5
    for s in a:s.validate()


def test_selection_does_not_use_future_result():
    h=['00000','00001','00002','00003','00004']*10
    x,details=choose_candidate_ids(algo(),h,k=100)
    y,_=choose_candidate_ids(algo(),list(h),k=100)
    assert np.array_equal(x,y) and len(set(x.tolist()))==100
    assert details['selection_sha256']


def test_null_and_development_only():
    rng=np.random.default_rng(44)
    seq=[f'{int(x):05d}' for x in rng.integers(0,100000,size=75)]
    report=full_audit(algo(),seq,eval_size=21,null_sequences=1,attempts=9)
    assert report['engineering_reproduced'] is True
    assert report['prediction_validated'] is False
    assert report['approved_for_research_registry'] is False
    assert report['development']['n']==21
    assert report['all_discovery_attempts_counted']==9


def test_registry_document_immutability_and_gated_approval(tmp_path):
    db=sqlite3.connect(tmp_path/'research.sqlite')
    r=ResearchRegistry(db)
    r.add_document('x','Paper','a scientific discovery on numerical sequences for testing')
    with pytest.raises(ValueError):r.add_document('x','Paper','changed scientific research with totally different data')
    r.add_algorithm(algo(),'x')
    report={'engineering_reproduced':True,'prediction_validated':False}
    audit=r.add_audit(algo().fingerprint(),'f'*64,report)
    assert r.has_audit(algo().fingerprint(),'f'*64)==audit['audit_id']
    with pytest.raises(PermissionError):r.approve_research_only(algo().fingerprint(),audit['audit_id'],'reviewer','')
    approved=r.approve_research_only(algo().fingerprint(),audit['audit_id'],'reviewer','I_APPROVE_RESEARCH_ONLY')
    assert approved['ranking_not_changed'] and not approved['prediction_validated']
    db.close()


def test_pipeline_idempotent_on_same_data(tmp_path):
    db=sqlite3.connect(tmp_path/'research.sqlite');r=ResearchRegistry(db)
    r.add_document('paperA','Document','conformal sequential statistical research evidence over many windows')
    rng=np.random.default_rng(11)
    seq=[f'{int(x):05d}' for x in rng.integers(0,100000,size=65)]
    h=hashlib.sha256('demo'.encode()).hexdigest()
    run_for_document(r,'paperA',seq,data_sha256=h,limit=2,eval_size=21,null_sequences=0)
    n=len(r.audits())
    run_for_document(r,'paperA',seq,data_sha256=h,limit=2,eval_size=21,null_sequences=0)
    assert len(r.audits())==n
    assert all(x['status']=='already_tested_on_this_dataset' for x in r.algorithms() and run_for_document(r,'paperA',seq,data_sha256=h,limit=2,eval_size=21,null_sequences=0)['experiments'])
    db.close()


def test_paper_source_whitelist_and_local_import(tmp_path):
    assert arxiv_id_from_metadata('https://arxiv.org/abs/2501.01234v3')=='2501.01234'
    with pytest.raises(ValueError):arxiv_id_from_metadata('https://evil.com/pdf/2501.01234')
    with pytest.raises(ValueError):arxiv_id_from_metadata('2201.00123/../../other')
    p=tmp_path/'paper.txt';p.write_text('This is a research text. Statistical evidence must be tested.')
    text,digest=read_local_document(p)
    assert text.startswith('This') and len(digest)==64


def test_mocked_llm_ast_rejected_no_execution(monkeypatch):
    class BadModel:
        class responses:
            @staticmethod
            def create(**kwargs):
                return type('Result',(),{'output_text':json.dumps({'algorithms':[{
                  'formula':{'kind':'metric','name':'__class__'},'pattern':'constant','window':3,'method_note':'bad'}]})})()
    with pytest.raises(ValueError):propose_with_model('real paper text','doc',client=BadModel())


def test_approved_research_rank_independent():
    from autoresearch.verification import rank_research_approved
    history=['00001','00022','00443','12345']*12
    choice,evidence=rank_research_approved([algo()],history,k=100)
    choice2,_=rank_research_approved([algo()],history,k=100)
    assert len(choice)==100 and len(set(choice))==100 and choice2==choice
    assert evidence['ranking_is_uncalibrated'] is True
    assert evidence['fair_baseline_coverage']==0.001


def test_local_pdf_fulltext(tmp_path):
    fitz=pytest.importorskip('fitz')
    d=fitz.open();p=d.new_page();p.insert_text((60,60),
        'Scientific manuscript: sequential distribution testing and valid uncertainty calibration.'*3)
    file=tmp_path/'study.pdf';file.write_bytes(d.tobytes());d.close()
    text,sha=read_local_document(file)
    assert 'Scientific manuscript' in text and len(sha)==64


def test_mocked_arxiv_download_rejects_html():
    def get(url):
        assert url=='https://arxiv.org/pdf/2501.01234'
        return b'<html>not pdf</html>'
    with pytest.raises(ValueError):fetch_arxiv_pdf('2501.01234',get_bytes=get)


def test_mocked_valid_llm_formula():
    class Model:
        class responses:
            @staticmethod
            def create(**kwargs):
                assert '不可信' in kwargs['input']
                return type('Result',(),{'output_text':json.dumps({'algorithms':[{
                    'formula':{'kind':'metric','name':'span'},'pattern':'constant',
                    'window':3,'method_note':'explore finite differences'}]})})()
    candidates=propose_with_model('untrusted text','paper',client=Model())
    assert len(candidates)==1 and candidates[0].formula['name']=='span'
