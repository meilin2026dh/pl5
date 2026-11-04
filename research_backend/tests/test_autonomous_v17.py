"""Offline safety and durability tests. Never call external network."""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import json
import pytest

from autoresearch.official_archive_v17 import OfficialArchive, validate_rows, parse_official
from autoresearch.supervisor_v17 import Supervisor, cycle_now, single_instance
from autoresearch.collectors import Paper


def official(issue='26290', date='2026-10-31', number='00127'):
    return {'success':True,'value':{'list':[{'lotteryGameNum':'350133',
        'lotteryDrawNum':issue,'lotteryDrawTime':date,'lotteryDrawResult':number}]}}


def test_official_parser_preserves_leading_zero_and_rejects_invalid():
    assert parse_official(official())[0]['number']=='00127'
    with pytest.raises(ValueError,match='彩种'):parse_official({'success':True,'value':{'list':[{'lotteryGameNum':'123'}]}})
    with pytest.raises(ValueError,match='日期'):parse_official(official(date='2026-02-30'))
    with pytest.raises(ValueError,match='五位'):parse_official(official(number='127'))


def test_official_archive_incremental_immutable(tmp_path):
    a=OfficialArchive(tmp_path/'archive')
    first={'issue':'1','date':'2026-10-30','number':'00000'}
    second={'issue':'2','date':'2026-10-31','number':'99999'}
    r1=a.merge([first]); p=a.snapshots/(r1['version']+'.json')
    assert p.exists() and r1['count']==1
    assert a.merge([first])['changed'] is False
    r2=a.merge([second]); assert r2['added']==1
    assert a.load()[0]==[first,second]
    assert p.exists() and (a.snapshots/(r2['version']+'.json')).exists()
    with pytest.raises(ValueError,match='冲突'):a.merge([{'issue':'1','date':'2026-10-30','number':'12345'}])
    assert a.load()[1]['version']==r2['version']
    assert '00000' in a.csv.read_text('utf8')


def test_tampered_archive_rejected(tmp_path):
    a=OfficialArchive(tmp_path)
    r=a.merge([{'issue':'1','date':'2026-10-30','number':'00000'}])
    (a.snapshots/(r['version']+'.json')).write_text('[]',encoding='utf8')
    with pytest.raises(ValueError,match='校验|索引'):a.load()


def test_invalid_duplicate_issue_or_date():
    with pytest.raises(ValueError):validate_rows([
        {'issue':'1','date':'2026-10-30','number':'00000'},
        {'issue':'1','date':'2026-10-30','number':'00001'}])
    with pytest.raises(ValueError):validate_rows([
        {'issue':'1','date':'2026-10-30','number':'00000'},
        {'issue':'2','date':'2026-10-30','number':'00000'}])


def test_cycle_utc():
    assert cycle_now(datetime(2026,11,1,23,tzinfo=timezone.utc))=='20261101-18'


def test_lock_rejects_second_invocation(tmp_path):
    with single_instance(tmp_path/'lock'):
        with pytest.raises(RuntimeError):
            with single_instance(tmp_path/'lock'):pass


def test_supervisor_retries_only_failed_stage(tmp_path):
    papers=[Paper('a','arxiv','Testing','Abstract','https://arxiv.org/a','2026-11-01','testing')]
    calls={'n':0}
    def flaky(key,cfg,docs,arc):
        calls['n']+=1
        if calls['n']==1:raise RuntimeError('transient')
        return {'state':'completed','run_id':'fake-research'}
    with Supervisor(tmp_path/'status.db',tmp_path/'archive',tmp_path/'papers.db') as s:
        with pytest.raises(RuntimeError,match='transient'):
            s.run(key='20261101-18',papers=papers,research_runner=flaky)
        r=s.run(key='20261101-18',papers=papers,research_runner=flaky)
        assert r['research']['state']=='completed'
        assert calls['n']==2
        s.run(key='20261101-18',papers=papers,research_runner=flaky)
        assert calls['n']==2
        x=s.status()['cycles'][0]
        assert x['state']=='completed'
        assert [st['attempts'] for st in x['stages']]==[1,2,1]
        with pytest.raises(ValueError,match='参数已封存'):
            s.run(key='20261101-18',papers=papers,topics=('changed topic',),research_runner=flaky)


def test_sync_online_only(tmp_path):
    with Supervisor(tmp_path/'state.sqlite',tmp_path/'archive',tmp_path/'papers.db') as s:
        with pytest.raises(ValueError,match='离线模式禁止'):
            s.run(key='20261101-00',papers=[],sync_official=True)


def test_end_to_end_offline_original_workflow(tmp_path):
    papers=[Paper('doi:demo','openalex','sequential testing robustness','This paper studies sequential testing and model uncertainty','https://doi.org/demo','2026-11-01','sequential testing')]
    with Supervisor(tmp_path/'status.db',tmp_path/'archive',tmp_path/'papers.db') as s:
        report=s.run(key='20261101-12',papers=papers)
        assert report['research']['state']=='completed'
        assert report['automatic_approval'] is False
        assert report['predictive_advantage_proven'] is False
        assert s.run(key='20261101-12',papers=papers)==report


def test_official_network_outage_does_not_stop_independent_research(tmp_path):
    papers=[]
    def failed(_):raise OSError('timeout simulated')
    called=[]
    def runner(key,cfg,docs,arc):
        called.append(key)
        return {'state':'completed','development_only':False}
    with Supervisor(tmp_path/'state.sqlite',tmp_path/'archive',tmp_path/'papers.sqlite') as s:
        out=s.run(key='20261101-06',mode='live',sync_official=True,audit=True,
                  archive_fetcher=failed,research_runner=runner)
        assert out['data']['state']=='network_unavailable'
        assert out['data']['development_audit_blocked']
        assert called==['20261101-06']


def test_conflicting_official_history_stops_research(tmp_path):
    called=[]
    with Supervisor(tmp_path/'state.sqlite',tmp_path/'archive',tmp_path/'papers.sqlite') as s:
        s.archive.merge([{'issue':'1','date':'2026-10-30','number':'00000'}])
        def bad(_):return [{'issue':'1','date':'2026-10-30','number':'00001'}]
        with pytest.raises(ValueError,match='冲突'):
            s.run(key='20261101-12',mode='live',sync_official=True,archive_fetcher=bad,
                  research_runner=lambda *_:called.append(1))
        assert not called
        assert s.status()['cycles'][0]['state']=='failed'


def test_read_only_status_does_not_create_db(tmp_path):
    from autoresearch.status_v17 import status
    p=tmp_path/'notcreated.sqlite'
    view=status(p,tmp_path/'archive')
    assert view['state']=='not_initialized'
    assert not p.exists()


def test_http_read_only_status_reports_completed_cycle(tmp_path,monkeypatch):
    from autoresearch.status_v17 import status
    papers=[]
    with Supervisor(tmp_path/'cycle.sqlite',tmp_path/'archive',tmp_path/'papers.sqlite') as s:
        s.run(key='test-slot',papers=papers,research_runner=lambda *args:{'state':'completed'})
    view=status(tmp_path/'cycle.sqlite',tmp_path/'archive')
    assert view['completed_cycles']==1
    assert view['last_cycle']['state']=='completed'
    assert view['automatic_algorithm_approval'] is False
