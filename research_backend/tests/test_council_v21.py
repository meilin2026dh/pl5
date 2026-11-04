"""Cooperative orchestration tests; Docker runners in tests are explicit fakes."""
from __future__ import annotations
import json,sqlite3
import pytest
from autoresearch.council_v21 import ResearchCouncil
from autoresearch.paper_factory_v20 import offline_blueprint
from autoresearch.proposals_v08 import DIGIT_COUNT_SOURCE, TRANSITION_SOURCE

BODY='''Statistical models can represent sequential patterns, but calibration must use a held-out
period of data. We estimate candidate scores from previous records and compare them to a
uniform baseline under independent validation to avoid exaggerated forecasting claims.'''

@pytest.fixture
def ctx(tmp_path):
    with sqlite3.connect(tmp_path/'council.sqlite') as db:
        r=ResearchCouncil(db)
        r.paper.documents.add_document('doc-example','Test independent sequence model',BODY,url='local:test',kind='local')
        b=r.paper.register_blueprint('doc-example',offline_blueprint(r.paper.documents.get_document('doc-example')))
        task=r.create(b['blueprint_id'],goal='Assess whether the sequence score can improve reproducible candidate filtering',budget=2,periods=2)
        yield r,task['project_id']

def test_plan_immutable_resume_and_source(ctx):
    r,pid=ctx
    assert r.create(r._project(pid)['blueprint_id'],goal=r._project(pid)['goal'],budget=2,periods=2)['created'] is False
    first=r.plan(pid)
    again=r.plan(pid)
    assert not again['literature']['created']
    assert first['state']=='in_progress'
    assert r.state(pid)['next_stage']=='engineer_primary'
    assert r.state(pid)['event_count']==3
    assert r.state(pid)['last_event_sha']!='0'*64
    with pytest.raises(sqlite3.DatabaseError):r.db.execute('DELETE FROM v21_projects')
    with pytest.raises(sqlite3.DatabaseError):r.db.execute('UPDATE v21_events SET actor="x"')
    assert r.state(pid)['prediction_advantage']=='NOT_ESTABLISHED'

def test_teams_need_two_sources_and_repeat_code_is_rejected(ctx):
    r,pid=ctx
    r.submit_code(pid,role='primary',source=DIGIT_COUNT_SOURCE)
    with pytest.raises(ValueError):r.red_team(pid)
    with pytest.raises(ValueError):r.submit_code(pid,role='reference',source=DIGIT_COUNT_SOURCE)
    r.submit_code(pid,role='reference',source=TRANSITION_SOURCE)
    check=r.red_team(pid)['review']
    assert not check['potential_copy']
    assert check['checks_implemented_as_tests'] is False
    assert len(check['issues'])>=4
    with pytest.raises(ValueError):r.submit_code(pid,role='primary',source=TRANSITION_SOURCE)

def test_no_code_execution_without_opt_in(ctx):
    r,pid=ctx
    r.submit_code(pid,role='primary',source=DIGIT_COUNT_SOURCE)
    r.submit_code(pid,role='reference',source=TRANSITION_SOURCE)
    with pytest.raises(PermissionError):r.audit(pid,['00000']*23)
    assert not r._artifact(pid,'sandbox_audit')
    with pytest.raises(ValueError):r.decision(pid)

def test_faked_sandbox_success_gives_manual_review_only(ctx):
    r,pid=ctx
    r.submit_code(pid,role='primary',source=DIGIT_COUNT_SOURCE)
    r.submit_code(pid,role='reference',source=TRANSITION_SOURCE)
    run=[]
    def fake(source,cases):
        run.append(source)
        return {'ranked':[case['candidates'][:case['k']] for case in cases]}
    result=r.audit(pid,['00000','00001']*12,allow_docker=True,runner=fake)
    assert result['report']['engineering_cross_check'] is True
    assert len(run)==4
    assert r.decision(pid)['decision']['research_engineering_status']=='manual_review_candidate'
    assert not r.decision(pid)['decision']['official_approval']
    assert r.state(pid)['state']=='research_review_pending'
    assert r.status()['total']==1
    with pytest.raises(ValueError):r.audit(pid,['00000','00001']*12,allow_docker=True,runner=fake)
    assert r.state(pid)['event_count']==8

def test_conflicting_reproduction_and_no_auto_promotion(ctx):
    r,pid=ctx
    r.submit_code(pid,role='primary',source=DIGIT_COUNT_SOURCE)
    r.submit_code(pid,role='reference',source=TRANSITION_SOURCE)
    def fake(src,cases):
        return {'ranked':[x['candidates'][-x['k']:] if 'table' in src else x['candidates'][:x['k']] for x in cases]}
    r.audit(pid,['00000','00001']*12,allow_docker=True,runner=fake)
    result=r.decision(pid)
    assert result['decision']['research_engineering_status']=='needs_new_experiment'
    assert not result['decision']['automatic_esse_activation']

def test_invalid_source_never_registered(ctx):
    r,pid=ctx
    with pytest.raises((ValueError,SyntaxError)):r.submit_code(pid,role='primary',source='import os\n'+DIGIT_COUNT_SOURCE)
    assert r.state(pid)['next_stage']=='engineer_primary'

def test_append_log_detects_tampering_even_if_triggers_disabled(ctx):
    r,pid=ctx
    r.plan(pid)
    r.db.execute('DROP TRIGGER v21_events_no_update')
    r.db.execute('UPDATE v21_events SET payload_json=? WHERE project_id=? AND stage=?', ('{}',pid,'literature'))
    r.db.commit()
    with pytest.raises(ValueError,match='审计链'):r.state(pid)

def test_rejected_invalid_history(ctx):
    r,pid=ctx
    r.submit_code(pid,role='primary',source=DIGIT_COUNT_SOURCE)
    r.submit_code(pid,role='reference',source=TRANSITION_SOURCE)
    with pytest.raises(ValueError,match='历史记录'):r.audit(pid,['bad']*10,allow_docker=True,runner=lambda *_: {})

def test_static_artefacts_do_not_certify_predictions(ctx):
    r,pid=ctx
    p=r.plan(pid)
    info=r._artifact(pid,'literature')
    assert info['quote'] in BODY
    assert not info['paper_reproduced']
    assert r._artifact(pid,'hypothesis')['forecast_advantage']=='not_established'
    assert not r.status()['auto_publish']


def test_auto_plan_bounded_idempotent(ctx):
    r,pid=ctx
    first=r.auto_plan(maximum=3)
    assert first['count']==1
    assert not first['untrusted_code_executed']
    assert first['created'][0]['next_stage']=='engineer_primary'
    second=r.auto_plan(maximum=3)
    assert second['count']==0
    assert r.status()['total']==2
