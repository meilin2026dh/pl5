from hashlib import sha256
import json
import sqlite3
from types import SimpleNamespace
import pytest
from autoresearch.python_lab_v08 import (inspect_python_source,docker_command,
  run_in_docker,build_walkforward_cases,audit_python_candidate,PythonResearchStore)
from autoresearch.proposals_v08 import TRANSITION_SOURCE,DIGIT_COUNT_SOURCE,offline_proposals,llm_python_proposal


@pytest.mark.parametrize('src',[TRANSITION_SOURCE,DIGIT_COUNT_SOURCE])
def test_templates_pass_static(src):
    assert inspect_python_source(src)['function']=='score_batch'


@pytest.mark.parametrize('bad',["import os\ndef score_batch(history,candidates):\n return []", 
  "def score_batch(history,candidates):\n return [open('/tmp/test') for x in candidates]",
  "def score_batch(history,candidates):\n return [().__class__ for x in candidates]",
  "def score_batch(history,candidates):\n import math\n return [1 for x in candidates]",
  "def score_batch(history,candidates):\n return [getattr(x,'__class__') for x in candidates]",
  "def score_batch(history,candidates):\n return [eval('1') for x in candidates]",
])
def test_forbidden_python_patterns(bad):
    with pytest.raises(ValueError):inspect_python_source(bad)


def test_requires_a_real_docker_engine(monkeypatch):
    monkeypatch.setattr('autoresearch.python_lab_v08.docker_available',lambda:False)
    with pytest.raises(RuntimeError,match='Docker'):
        run_in_docker(DIGIT_COUNT_SOURCE,[{'history':['12345'],'candidates':['00000'],'k':1}])


def test_docker_hardening_flags(monkeypatch):
    monkeypatch.setattr('shutil.which',lambda n:'/usr/bin/docker')
    args=docker_command('/tmp/example')
    for key in ['--network','none','--read-only','--cap-drop','ALL','--security-opt',
                'no-new-privileges=true','--pids-limit','--memory','--cpus','--user','--mount']:
        assert key in args
    assert args[-5:]==['python:3.12-alpine','python','-I','-B','/work/runner.py']


def test_container_response_validation_with_mock(monkeypatch):
    monkeypatch.setattr('autoresearch.python_lab_v08.docker_available',lambda:True)
    monkeypatch.setattr('shutil.which',lambda n:'/usr/bin/docker')
    out=run_in_docker(DIGIT_COUNT_SOURCE,[{'history':['00000'],'candidates':['00000','00001'],'k':1}],
                      run=lambda *a,**kw:SimpleNamespace(returncode=0,stdout='{"ranked":[["00001"]]}',stderr=''))
    assert out['ranked']==[['00001']]


def test_container_rejects_unsupported_numbers(monkeypatch):
    monkeypatch.setattr('autoresearch.python_lab_v08.docker_available',lambda:True)
    with pytest.raises(ValueError):run_in_docker(DIGIT_COUNT_SOURCE,[{'history':[],'candidates':['1'],'k':1}])


def test_registry_immutable_and_duplicate_audit():
    db=sqlite3.connect(':memory:')
    reg=PythonResearchStore(db)
    info=reg.add(document_key='paper-001',source=DIGIT_COUNT_SOURCE,origin='offline_template',
                 method_claim='这是一个待验证的分布频数算法研究假说。')
    assert reg.get(info['code_id'])['source']==DIGIT_COUNT_SOURCE
    assert not reg.add(document_key='paper-001',source=DIGIT_COUNT_SOURCE,origin='offline_template',
                       method_claim='这是一个待验证的分布频数算法研究假说。')['new']
    def fake_runner(code,draws,**kw):return {'status':'exploratory_only','hits':0}
    data=['12345']*50
    res=reg.audit(info['code_id'],data,data_digest=sha256(b'abc').hexdigest(),runner=fake_runner)
    assert res['auto_activated'] is False
    with pytest.raises(ValueError,match='重复筛选'):
        reg.audit(info['code_id'],data,data_digest=sha256(b'abc').hexdigest(),runner=fake_runner)


def test_audit_exact_100k_and_repeat(monkeypatch):
    draws=['%05d'%i for i in range(31)]
    calls=[]
    def fake_runner(source,cases):
        calls.append(cases)
        assert all(len(c['candidates'])==100000 for c in cases)
        return {'ranked':[[f'{i:05d}' for i in range(100)] for _ in cases]}
    report=audit_python_candidate(DIGIT_COUNT_SOURCE,draws,k=100,eval_size=3,docker_run=fake_runner)
    assert report['two_runs_identical'] and len(calls)==2
    assert report['hits']==3 # first 100 numbers contain last three synthetic results
    assert report['must_not_use_as_proof']


def test_nonreproducible_is_rejected():
    i=[0]
    def non_deterministic(src,cases):
        i[0]+=1
        return {'ranked':[['00001' if i[0]%2 else '00002'] for _ in cases]}
    with pytest.raises(RuntimeError,match='复现失败'):
        audit_python_candidate(DIGIT_COUNT_SOURCE,['00000']*50,k=1,eval_size=2,docker_run=non_deterministic)


def test_offline_not_misrepresented_as_faithful():
    docs={'title':'Markov Model','text_excerpt':'The sequence method is under study.'}
    props=offline_proposals(docs)
    assert len(props)==2
    assert all('不是论文原' in x['method_claim'] or '不声称复现' in x['method_claim'] for x in props)


def test_llm_schema_with_mock_client():
    class Client:
        class responses:
            @staticmethod
            def create(**kwargs):
                return SimpleNamespace(output_text=json.dumps({'source':DIGIT_COUNT_SOURCE,
                               'method_claim':'有条件的数据建模假设，尚无独立证据支持。'}))
    out=llm_python_proposal({'text_excerpt':'some text'},client=Client())
    assert out['origin']=='llm_opt_in'
    inspect_python_source(out['source'])


def test_proposal_attempt_tracking():
    db=sqlite3.connect(':memory:')
    lab=PythonResearchStore(db)
    assert not lab.has_proposal_attempt('doc1','offline_template')
    lab.register_proposal_attempt('doc1','offline_template')
    assert lab.has_proposal_attempt('doc1','offline_template')
    lab.register_proposal_attempt('doc1','offline_template')
    assert db.execute('SELECT count(*) FROM v08_proposal_attempts').fetchone()[0]==1


def test_source_links_for_dedup():
    db=sqlite3.connect(':memory:')
    lab=PythonResearchStore(db)
    claim='这是论文启发的算法假设，并无预测有效性的独立证据。'
    lab.add(document_key='p1',source=TRANSITION_SOURCE,origin='offline_template',method_claim=claim)
    lab.add(document_key='p2',source=TRANSITION_SOURCE,origin='offline_template',method_claim=claim)
    assert db.execute('SELECT count(*) FROM v08_python_candidates').fetchone()[0]==1
    assert db.execute('SELECT count(*) FROM v08_source_links').fetchone()[0]==2
