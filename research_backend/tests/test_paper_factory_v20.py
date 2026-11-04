"""V2.0 evidence grounding, immutable research and container-gated pair evaluation."""
from __future__ import annotations
import json
import sqlite3
from types import SimpleNamespace
import pytest
from autoresearch.paper_factory_v20 import PaperFactory,offline_blueprint,validate_blueprint,llm_blueprint
from autoresearch.proposals_v08 import DIGIT_COUNT_SOURCE, TRANSITION_SOURCE

BODY='''Methods and models can be combined, but statistical calibration must be performed with
training data independent of the test set. We estimate a transition probability matrix
using historical counts, then evaluate forecasts against a uniform reference distribution.
A withheld set is kept for evaluation and cannot be reused after model selection.'''

@pytest.fixture
def factory(tmp_path):
    with sqlite3.connect(tmp_path/'papers.sqlite') as db:
        f=PaperFactory(db)
        f.documents.add_document('doc1','Methodological example with transition models',BODY,kind='local',url='file:example')
        yield f

def test_offline_extract_is_grounded_and_idempotent(factory):
    card=offline_blueprint(factory.documents.get_document('doc1'))
    out=factory.register_blueprint('doc1',card,mode='offline_unreviewed')
    again=factory.register_blueprint('doc1',card,mode='offline_unreviewed')
    assert out['citation_verified'] and out['created'] and not again['created']
    assert factory.capability_card(out['blueprint_id'])['source']['source_quote'] in BODY
    assert factory.status()['approved_predictive_algorithms']==0
    assert factory.auto_extract()['count']==0


def test_fake_citation_and_abstract_claim_rejected(factory):
    card=offline_blueprint(factory.documents.get_document('doc1'))
    with pytest.raises(ValueError,match='逐字定位'):
        factory.register_blueprint('doc1',{**card,'excerpt':'The lottery will be predicted for certain.'})
    with pytest.raises(ValueError,match='字段'):
        factory.register_blueprint('doc1',{**card,'malicious':'run command'})
    factory.documents.add_document('abstract','A research abstract',BODY,kind='abstract')
    with pytest.raises(ValueError,match='摘要'):
        factory.register_blueprint('abstract',{**card,'method_type':'author_method_candidate'})


def test_llm_requires_consent_and_verbatim_grounding(factory):
    doc=factory.documents.get_document('doc1')
    with pytest.raises(PermissionError):llm_blueprint(doc,confirm_paid=False)
    card=offline_blueprint(doc)
    class Fake:
        responses=SimpleNamespace(create=lambda **kw: SimpleNamespace(output_text=json.dumps(card)))
    assert llm_blueprint(doc,confirm_paid=True,client=Fake())['excerpt'] in BODY
    bad={**card,'excerpt':'Completely invented paper quotation from nowhere'}
    class Bad:
        responses=SimpleNamespace(create=lambda **kw: SimpleNamespace(output_text=json.dumps(bad)))
    with pytest.raises(ValueError):llm_blueprint(doc,confirm_paid=True,client=Bad())


def test_code_links_immutable_and_malicious_source_rejected(factory):
    bid=factory.auto_extract()['created'][0]['blueprint_id']
    a=factory.link_code(bid,DIGIT_COUNT_SOURCE,role='primary')
    assert a['source_executed'] is False
    assert factory.capability_card(bid)['code_sha256']['primary']==a['code_id']
    with pytest.raises(ValueError):factory.link_code(bid,TRANSITION_SOURCE,role='primary')
    with pytest.raises(ValueError):factory.link_code(bid,DIGIT_COUNT_SOURCE,role='reference')
    with pytest.raises((ValueError,SyntaxError)):
        factory.link_code(bid,'import os\n'+DIGIT_COUNT_SOURCE,role='reference')
    factory.link_code(bid,TRANSITION_SOURCE,role='reference')
    with pytest.raises(PermissionError):factory.study(bid,['00000']*23)


def test_explicit_container_gate_and_append_only_study(factory):
    bid=factory.auto_extract()['created'][0]['blueprint_id']
    factory.link_code(bid,DIGIT_COUNT_SOURCE,role='primary')
    factory.link_code(bid,TRANSITION_SOURCE,role='reference')
    calls=[]
    def stub(src,cases):
        calls.append(src)
        return {'ranked':[c['candidates'][:c['k']] for c in cases]}
    draws=['00000','00001']*12
    report=factory.study(bid,draws,budget=2,periods=2,allow_docker=True,runner=stub)
    assert report['engineering_cross_check'] and len(calls)==4
    assert not report['prediction_improvement_proven']
    assert factory.status()['total_studies']==1
    with pytest.raises(ValueError,match='已经使用'):
        factory.study(bid,draws,budget=2,periods=2,allow_docker=True,runner=stub)
    assert len(calls)==4
    with pytest.raises(sqlite3.DatabaseError):
        factory.db.execute('UPDATE v20_studies SET budget=3')
    assert factory.capability_card(bid)['status']=='sandbox_compared_research_only'


def test_inconsistent_reference_prevents_engineering_pass(factory):
    bid=factory.auto_extract()['created'][0]['blueprint_id']
    factory.link_code(bid,DIGIT_COUNT_SOURCE,role='primary')
    factory.link_code(bid,TRANSITION_SOURCE,role='reference')
    def stub(src,cases):
        choices=[c['candidates'][-c['k']:] if 'table' in src else c['candidates'][:c['k']] for c in cases]
        return {'ranked':choices}
    r=factory.study(bid,['12345']*22,budget=1,periods=2,allow_docker=True,runner=stub)
    assert not r['engineering_cross_check'] and not r['same_top_k_all_periods']


def test_no_substituting_invalid_container_output(factory):
    bid=factory.auto_extract()['created'][0]['blueprint_id']
    factory.link_code(bid,DIGIT_COUNT_SOURCE,role='primary')
    factory.link_code(bid,TRANSITION_SOURCE,role='reference')
    def malicious_runner(src,cases):return {'ranked':[['not-valid'] for _ in cases]}
    with pytest.raises(ValueError,match='沙箱返回'):
        factory.study(bid,['12345']*22,budget=1,periods=2,allow_docker=True,runner=malicious_runner)
    assert factory.status()['total_studies']==0
