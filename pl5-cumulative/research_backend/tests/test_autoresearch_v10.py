import json
import sqlite3
from hashlib import sha256
from pathlib import Path
import pytest

from autoresearch.collectors import Paper
from autoresearch.integrated_v10 import ResearchCoordinator, sha
from autoresearch.bundles_v10 import CandidateBundles, history
from autoresearch.store import LabStore
from research_v10 import demo

ROOT=Path(__file__).resolve().parents[1]


def papers():
    return [Paper('demo:001','arxiv','Sequential multiple testing of random sequences',
                  'This is a synthetic test abstract about sequential multiple testing with e-values '
                  'and no claim that a random lottery can be predicted. Data are solely for testing.',
                  'https://example.org/demo','2026-01-01','sequential multiple testing','Synthetic')]


def cfg(fixture_papers=None,**overrides):
    pp=fixture_papers if fixture_papers is not None else papers()
    result={'mode':'offline','fixture':sha([p.to_dict() for p in pp]),
            'topics':['sequential multiple testing'],'providers':['arxiv'],
            'max_documents':1,'max_formulas':1,'max_code_proposals':1}
    result.update(overrides)
    return result


def makecsv(path,n=80):
    rows=['period,number'] + [f'{20261000+i},{(i*271+17)%100000:05d}' for i in range(1,n+1)]
    path.write_text('\n'.join(rows)+'\n',encoding='utf-8')
    return path


def test_end_to_end_offline_resume_idempotent(tmp_path):
    with LabStore(tmp_path/'db.sqlite') as s:
        ctl=ResearchCoordinator(s)
        p=papers()
        rid=ctl.create(cfg(p),run_id='run_001')
        first=ctl.run(rid,fixture_papers=p)
        second=ctl.run(rid,fixture_papers=p)
        assert second['status']=='completed'
        assert len(first['steps'])==7
        assert len(ctl.status(rid)['steps'])==7
        assert all(x['attempts']==1 for x in ctl.status(rid)['steps'])
        assert ctl.status(rid)['budget']['paid_model_calls']==0
        assert first['steps']['propose_python']['code_executed'] is False
        assert first['steps']['review']['auto_predictive_claim'] is False


def test_run_id_config_immutability(tmp_path):
    with LabStore(tmp_path/'db.sqlite') as s:
        c=ResearchCoordinator(s)
        c.create(cfg(),run_id='run_id')
        with pytest.raises(ValueError,match='不可变更'):
            c.create(cfg(max_documents=2),run_id='run_id')


def test_cannot_forge_fixture_or_mutate_status(tmp_path):
    with LabStore(tmp_path/'db.sqlite') as s:
        c=ResearchCoordinator(s)
        rid=c.create(cfg(),run_id='run_test')
        bad=[Paper('demo:bad','arxiv','test','bad description','url','2026','x','synthetic')]
        with pytest.raises(ValueError,match='摘要'):
            c.run(rid,fixture_papers=bad)
        c.run(rid,fixture_papers=papers())
        s.db.execute("UPDATE v10_steps SET result_sha256='deadbeef' WHERE step='review'")
        s.db.commit()
        with pytest.raises(RuntimeError,match='摘要校验失败'):
            c.run(rid,fixture_papers=papers())


def test_retry_failure_records_checkpoint(tmp_path,monkeypatch):
    with LabStore(tmp_path/'db.sqlite') as s:
        c=ResearchCoordinator(s); rid=c.create(cfg(),run_id='run_fail')
        orig=c.store.upsert_papers
        def fail(*a,**kw):
            raise RuntimeError('simulated interruption')
        monkeypatch.setattr(s,'upsert_papers',fail)
        with pytest.raises(RuntimeError,match='simulated'):
            c.run(rid,fixture_papers=papers())
        assert c.status(rid)['status']=='failed'
        monkeypatch.setattr(s,'upsert_papers',orig)
        c.run(rid,fixture_papers=papers())
        assert c.status(rid)['status']=='completed'
        assert next(x for x in c.status(rid)['steps'] if x['step']=='discover')['attempts']==2


def test_budget_and_unattended_restrictions(tmp_path):
    with LabStore(tmp_path/'db.sqlite') as s:
        c=ResearchCoordinator(s)
        with pytest.raises(PermissionError):c.create(cfg(paid_llm=True))
        with pytest.raises(PermissionError):c.create(cfg(auto_approve=True))
        with pytest.raises(PermissionError):c.create(cfg(auto_execute_generated_code=True))
        rid=c.create(cfg(topics=['aa','bb','cc'],providers=['arxiv','github'],max_requests=3))
        with pytest.raises(PermissionError,match='预算'):
            c.run(rid,fixture_papers=papers())
        assert s.db.execute('SELECT count(*) FROM v10_steps').fetchone()[0]==0


def test_offline_requires_digest_and_live_no_fixture(tmp_path):
    with LabStore(tmp_path/'db.sqlite') as s:
        c=ResearchCoordinator(s)
        with pytest.raises(ValueError):c.create({'mode':'offline','topics':['a'],'providers':['arxiv']})
        with pytest.raises(ValueError):c.create({'mode':'live','topics':['a'],'providers':['arxiv'],'fixture':'x'})


def test_development_requires_frozen_data_source(tmp_path):
    with LabStore(tmp_path/'db.sqlite') as s:
        c=ResearchCoordinator(s)
        p=papers();nums=['00000']*80
        bad=cfg(p,enable_development_audit=True,dataset_sha256=sha(nums),official_source='official:user-declared')
        rid=c.create(bad,run_id='run_development')
        with pytest.raises(ValueError,match='不匹配'):
            c.run(rid,fixture_papers=p,history_numbers=['00001']*80)
        assert c.status(rid)['status']=='pending'


def test_local_bundle_deterministic_verified_immutable(tmp_path):
    csv=makecsv(tmp_path/'synthetic.csv')
    with LabStore(tmp_path/'db.sqlite') as s:
        c=CandidateBundles(s.db,ROOT)
        record=c.issue(csv_path=csv,official_source='official:test-not-a-verified-draw',
                       target_period='20261100',k=17,output_dir=tmp_path/'packets',
                       allow_empty_baseline=True)
        assert record['candidate_count']==17
        assert not record['trusted_pre_draw_proof']
        v=c.verify(record['artifact_path'],csv,require_model_in_ledger=True)
        assert v['verified_locally'] and not v['external_timestamp_verified']
        with pytest.raises(ValueError,match='已经封存'):
            c.issue(csv_path=csv,official_source='official:test-not-a-verified-draw',
                    target_period='20261100',k=17,output_dir=tmp_path/'packets',
                    allow_empty_baseline=True)
        with pytest.raises(sqlite3.IntegrityError):
            s.db.execute('DELETE FROM v10_bundles')


def test_tampering_history_and_bundle_detected(tmp_path):
    csv=makecsv(tmp_path/'synthetic.csv')
    with LabStore(tmp_path/'db.sqlite') as s:
        c=CandidateBundles(s.db,ROOT)
        rec=c.issue(csv_path=csv,official_source='official:test-not-a-verified-draw',
                    target_period='20261100',k=9,output_dir=tmp_path/'p',allow_empty_baseline=True)
        artifact=Path(rec['artifact_path'])
        pristine=artifact.read_text(encoding='utf-8')
        manifest=json.loads(pristine)
        manifest['candidates'][0]='99998'
        artifact.write_text(json.dumps(manifest),encoding='utf-8')
        assert not c.verify(artifact,csv)['verified_locally']
        artifact.write_text(pristine,encoding='utf-8')
        # Change a valid historical number without changing the period count.
        text=csv.read_text(encoding='utf-8')
        assert '00288' in text
        csv.write_text(text.replace('00288','00289'),encoding='utf-8')
        assert not c.verify(artifact,csv)['verified_locally']


def test_reject_late_seal_and_missing_rules(tmp_path):
    csv=makecsv(tmp_path/'synthetic.csv')
    with LabStore(tmp_path/'db.sqlite') as s:
        c=CandidateBundles(s.db,ROOT)
        with pytest.raises(ValueError,match='当前未设定shadow'):
            c.issue(csv_path=csv,official_source='official:test',target_period='20261100',
                   output_dir=tmp_path/'p')
        with pytest.raises(ValueError,match='目标期号'):
            c.issue(csv_path=csv,official_source='official:test',target_period='20261080',
                   output_dir=tmp_path/'p',allow_empty_baseline=True)


def test_demo_smoke():
    r=demo()
    assert r['steps_completed']==7 and r['steps_idempotent'] and r['paid_calls']==0


def test_live_source_failure_retry(tmp_path,monkeypatch):
    import autoresearch.integrated_v10 as v10
    with LabStore(tmp_path/'db.sqlite') as s:
        c=ResearchCoordinator(s)
        rid=c.create({'mode':'live','topics':['randomness testing'],'providers':['openalex']},run_id='run_live')
        monkeypatch.setattr(v10,'collect_all',lambda *a,**kw:([],[{'provider':'openalex','error':'simulated outage'}]))
        with pytest.raises(RuntimeError,match='所有外部'):
            c.run(rid)
        assert c.status(rid)['status']=='failed'
        monkeypatch.setattr(v10,'collect_all',lambda *a,**kw:(papers(),[]))
        result=c.run(rid)
        assert result['status']=='completed'
        assert next(x['attempts'] for x in c.status(rid)['steps'] if x['step']=='discover')==2


def test_shadow_rank_recomputed_from_frozen_rules(tmp_path):
    from autoresearch.lab import Hypothesis
    csv=makecsv(tmp_path/'synthetic.csv')
    with LabStore(tmp_path/'db.sqlite') as s:
        s.upsert_papers(papers(),lambda p:4.0)
        spec=Hypothesis('sum','constant',3)
        s.add_hypothesis(spec,papers()[0].key)
        s.set_status(spec.fingerprint(),'shadow')
        c=CandidateBundles(s.db,ROOT)
        record=c.issue(csv_path=csv,official_source='official:test-synthetic-only',
                       target_period='20261100',k=37,output_dir=tmp_path/'p')
        out=c.verify(record['artifact_path'],csv,require_model_in_ledger=True)
        assert out['verified_locally']
        manifest=json.loads(Path(record['artifact_path']).read_text(encoding='utf-8'))
        assert manifest['model']['specifications'][0]['indicator']=='sum'
        assert len(manifest['candidates'])==37


def test_fresh_offline_config_zero_paid_and_no_code_exec(tmp_path):
    with LabStore(tmp_path/'db.sqlite') as s:
        c=ResearchCoordinator(s)
        key=c.create(cfg(),run_id='run_no_remote')
        report=c.run(key,fixture_papers=papers())
        assert report['steps']['audit']['status']=='skipped_no_official_data'
        assert report['steps']['propose_python']['code_executed'] is False
        assert report['steps']['review']['automatic_formal_admission'] is False
