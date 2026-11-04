import hashlib
import json
import sqlite3
import pytest
from pathlib import Path

from autoresearch.collectors import Paper,collect_openalex,collect_arxiv,collect_github
from autoresearch.lab import Hypothesis, rank_100,walk_forward, propose, rule_mask
from autoresearch.store import LabStore
from autoresearch.prospective import precommit,settle_from_history,outcome_report

H='a'*64
A='b'*64

def test_openalex_mock_request_limits():
    seen=[]
    def fake_get(url):
        seen.append(url)
        return {'results':[{'doi':'https://doi.org/10.1000/test','display_name':'Randomness testing',
                             'publication_date':'2026-10-15','abstract_inverted_index':{'Hello':[0], 'world':[1]},
                             'authorships':[{'author':{'display_name':'Ada'}}]}]}
    items=collect_openalex('randomness testing','2026-10-01',get=fake_get)
    assert len(items)==1 and items[0].abstract=='Hello world' and 'per_page=8' in seen[0]


def test_arxiv_mock_atom():
    xml=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
        <id>https://arxiv.org/abs/2601.12345</id><title>Test Paper</title>
        <published>2026-10-11T00:00:00Z</published><summary>Alpha</summary>
        <author><name>Test Author</name></author></entry></feed>'''
    items=collect_arxiv('test research',get=lambda u:xml)
    assert len(items)==1 and items[0].authors=='Test Author'


def test_github_mock_json():
    items=collect_github('pattern science','2026-10-01',get=lambda u:{'items':[{'id':9,'full_name':'a/b','description':'safe metadata', 'html_url':'https://github.com/a/b','pushed_at':'2026-11-01T11:00:00Z','license':{'spdx_id':'MIT'}}]})
    assert len(items)==1 and items[0].source=='github'


def test_research_store_dedup_and_provenance(tmp_path):
    paper=Paper('doi-test','openalex','Sequential multiple testing','test','https://doi.org/test','2026-10-01','sequential multiple testing')
    with LabStore(tmp_path/'research.sqlite') as db:
        assert db.upsert_papers([paper],lambda p:5)==1
        assert db.upsert_papers([paper],lambda p:5)==0
        specs=propose(paper)
        assert specs
        assert db.add_hypothesis(specs[0],paper.key)
        assert not db.add_hypothesis(specs[0],paper.key)
        assert len(db.hypotheses())==1 and db.hypotheses()[0]['sources']==1
        with pytest.raises(ValueError):
            db.set_status(specs[0].fingerprint(),'approved')


def test_rank_is_bounded_and_reproducible():
    history=[f'{i:05d}' for i in range(70)]
    rules=[Hypothesis('sum','arithmetic',3)]
    picked1,ev1=rank_100(history,rules,k=100)
    picked2,ev2=rank_100(history,rules,k=100)
    assert picked1==picked2 and ev1==ev2
    assert len(picked1)==len(set(picked1))==100
    assert all(len(v)==5 for v in picked1)
    with pytest.raises(ValueError): rank_100(history,rules,k=101)


def test_prospective_immutable_and_future_only(tmp_path):
    with LabStore(tmp_path/'research.sqlite') as db:
        with pytest.raises(ValueError):
            precommit(db.db,target_period='26001',previous_period='26001',candidates=['00001'],
                      history_sha256=H,algorithm_sha256=A,source_description='official:manual')
        commit=precommit(db.db,target_period='26002',previous_period='26001',candidates=['00001','00002'],
                      history_sha256=H,algorithm_sha256=A,source_description='official:manual')
        assert commit['count']==2 and len(commit['commitment_sha256'])==64
        with pytest.raises(sqlite3.IntegrityError):
            precommit(db.db,target_period='26002',previous_period='26001',candidates=['99999'],
                      history_sha256=H,algorithm_sha256=A,source_description='official:manual')
        with pytest.raises(sqlite3.IntegrityError):
            db.db.execute("UPDATE predictions SET candidates_json='[]'")
        assert settle_from_history(db.db,period_to_number={'26001':'00001'},data_sha256=H,
                                   source_description='official:manual')['newly_settled']==0
        assert settle_from_history(db.db,period_to_number={'26002':'00002'},data_sha256=H,
                                   source_description='official:manual')['newly_settled']==1
        assert settle_from_history(db.db,period_to_number={'26002':'00002'},data_sha256=H,
                                   source_description='official:manual')['newly_settled']==0
        report=outcome_report(db.db)
        assert report['observed_hits']==1 and report['observed_periods']==1 and not report['guarantees_win_within_10']
        with pytest.raises(sqlite3.IntegrityError):
            db.db.execute("DELETE FROM outcomes")


def test_ten_period_report_baseline(tmp_path):
    with LabStore(tmp_path/'research.sqlite') as db:
        for i in range(1,11):
            precommit(db.db,target_period=f'260{i:02d}',previous_period=f'260{i-1:02d}',
                      candidates=['00001']*0+['00001'],history_sha256=H,algorithm_sha256=A,
                      source_description='official:manual')
        lookup={f'260{i:02d}':'00002' for i in range(1,11)}
        settle_from_history(db.db,period_to_number=lookup,data_sha256=H,
                            source_description='official:manual')
        report=outcome_report(db.db)
        assert len(report['rolling_10_period_windows'])==1
        assert report['rolling_10_period_windows'][0]['random_baseline_any_hit']==pytest.approx(1-(1-1/100000)**10)


def test_llm_abstract_is_schema_checked_without_network(tmp_path):
    from autoresearch.llm import analyze_abstract
    paper=Paper('a','arxiv','Online conformal research','summary','https://arxiv.org/abs/x','2026-10-31','conformal')
    class Response:
        output_text=json.dumps({'method':'自适应置信集','limitation':'公平开奖不产生信息','testable_idea':'在开发集测试经验覆盖率',
                                'related_to_lottery':True,'indicator':'sum','pattern':'constant','window':3,'transform':'raw'})
    class Client:
        class responses:
            @staticmethod
            def create(**kwargs):
                assert '不要markdown' in kwargs['instructions']
                return Response()
    card,spec=analyze_abstract(paper,client=Client(),model='local-mock')
    assert card['method'] and spec.indicator=='sum'
    with LabStore(tmp_path/'knowledge.sqlite') as db:
        db.upsert_papers([paper],lambda _:5)
        db.add_literature_card(paper.key,card,spec)
        assert db.literature_cards()[0]['card']['model']=='local-mock'


def test_llm_rejects_unknown_executable_rule():
    from autoresearch.llm import analyze_abstract
    paper=Paper('a','arxiv','Title','abstract','https://arxiv.org','2026-11-01','testing')
    class Response:
        output_text=json.dumps({'method':'X','limitation':'Y','testable_idea':'Z',
                                'related_to_lottery':True,'indicator':'__import__("os")',
                                'pattern':'constant','window':3,'transform':'raw'})
    class Client:
        class responses:
            @staticmethod
            def create(**kwargs):return Response()
    with pytest.raises(ValueError):analyze_abstract(paper,client=Client())
