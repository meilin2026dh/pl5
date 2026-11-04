import hashlib
import json
import math
import sqlite3
import pytest
from autoresearch.proposals_v08 import DIGIT_COUNT_SOURCE, TRANSITION_SOURCE
from autoresearch.python_lab_v08 import PythonResearchStore
from autoresearch.replication_v09 import (ReplicationRegistry,pure_python_reference,numpy_reference,
        verify_independent_kernels)
from autoresearch.evidence_v09 import EvidenceLedger,log_e_value
from research_v09 import demo


@pytest.fixture
def ready():
    db=sqlite3.connect(':memory:')
    lab=PythonResearchStore(db)
    registry=ReplicationRegistry(db)
    ledger=EvidenceLedger(db)
    cid=lab.add(document_key='p',source=DIGIT_COUNT_SOURCE,origin='offline_template',
                method_claim='一个研究性模型，没有经正式前向验证与论文复现。')['code_id']
    samples=['00000','12345','00999','88888']
    protocol=registry.create(document_key='p',code_id=cid,method_name='digit_sum',
       method_type='method_adaptation',paper_locator='paper p2 equation 5',
       math_assumptions='five digits and no future info',procedure='two independent math implementations',
       expected_fixture={'numbers':samples,'expected':pure_python_reference('digit_sum',samples)})
    return db, registry, ledger, cid, protocol['protocol_id']


@pytest.mark.parametrize('method', ['digit_sum','odd_count','transition_count'])
def test_builtins_all_100k(method):
    r=verify_independent_kernels(method)
    assert r['equivalent'] and r['tested']==100000


def test_invalid_fixtures_and_method(ready):
    db,reg,ledger,cid,pid=ready
    with pytest.raises(ValueError,match='未知'):
        numpy_reference('fake',['12345'])
    with pytest.raises(ValueError,match='五位'):
        pure_python_reference('digit_sum',['1234'])
    with pytest.raises(ValueError,match='参考样例'):
        reg.create(document_key='p',code_id=cid,method_name='digit_sum',method_type='method_adaptation',
                   paper_locator='equation 1',math_assumptions='digits',procedure='test',
                   expected_fixture={'numbers':['00000'],'expected':[]})


def test_paper_is_not_claimed_reproduced(ready):
    db,reg,ledger,cid,pid=ready
    r=reg.verify_builtin(pid,exhaustive=False)
    assert r['engineering_reproduced'] and not r['faithful_paper_reproduced']
    assert r['cross_check']['equivalent']
    assert reg.get(pid)['method_type']=='method_adaptation'


def test_bad_fixture_is_rejected_for_engineering(ready):
    db,reg,ledger,cid,pid=ready
    p=reg.create(document_key='p',code_id=cid,method_name='digit_sum',
      method_type='claimed_author_reproduction',paper_locator='p1 equation1',
      math_assumptions='digit',procedure='independent review',
      expected_fixture={'numbers':['12345'],'expected':[888]})
    r=reg.verify_builtin(p['protocol_id'],exhaustive=False)
    assert not r['engineering_reproduced'] and not r['faithful_paper_reproduced']


def test_protocol_immutable_and_digest(ready):
    db,reg,ledger,cid,pid=ready
    with pytest.raises(sqlite3.IntegrityError):
        db.execute('UPDATE v09_protocols SET method_name=? WHERE protocol_id=?',('broken',pid))
    assert reg.get(pid)['protocol_id']==pid


def test_registration_budget_telescope(ready):
    db,reg,ledger,cid,pid=ready
    for i in range(1,31):
        model=ledger.register_model(model_id=f'm_{i}',code_sha256=cid,
              protocol_id=pid,reviewer='human')
        assert model['alpha_allocated']==pytest.approx(0.05/(i*(i+1)))
    report=ledger.family_report()
    assert report['mathematical_budget_not_exceeded']
    assert report['alpha_spent']==pytest.approx(0.05*(1-1/31))


def test_unregistered_code_rejected(ready):
    db,reg,ledger,cid,pid=ready
    with pytest.raises(ValueError,match='V0.8'):
        ledger.register_model(model_id='abc',code_sha256='1'*64,
           protocol_id=pid,reviewer='human')
    with pytest.raises(ValueError,match='协议'):
        ledger.register_model(model_id='abc',code_sha256=cid,
           protocol_id='1'*64,reviewer='human')


def test_seal_settle_in_order_hash(ready):
    db,reg,ledger,cid,pid=ready
    ledger.register_model(model_id='model-01',code_sha256=cid,protocol_id=pid,reviewer='reviewed')
    s=ledger.seal(model_id='model-01',target_period='20260002',previous_period='20260001',
        candidates=['00000','00001'],history_sha256='a'*64,source_description='official:manually checked')
    assert s['k']==2
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("DELETE FROM v09_commits WHERE model_id='model-01'")
    with pytest.raises(ValueError,match='严格递增'):
        ledger.seal(model_id='model-01',target_period='20260001',previous_period='20260000',
            candidates=['12345'],history_sha256='a'*64,source_description='official:test')
    ledger.settle(target_period='20260002',number='00000',
        source_description='official:manually checked',data_sha256='b'*64)
    report=ledger.model_report('model-01')
    assert report['hits_in_prefix']==1 and report['record_hash_integrity']
    assert report['verified_prefix']==1 and report['predictive_edge_proven'] is False
    with pytest.raises((sqlite3.IntegrityError,ValueError)):
        ledger.settle(target_period='20260002',number='00001',
           source_description='official:changed',data_sha256='c'*64)
    with pytest.raises(ValueError,match='已入库'):
        ledger.seal(model_id='model-01',target_period='20260002',previous_period='20260001',
            candidates=['55555'],history_sha256='a'*64,source_description='official:late')


def test_no_result_in_gap_blocks_evidence(ready):
    db,reg,ledger,cid,pid=ready
    ledger.register_model(model_id='model-01',code_sha256=cid,protocol_id=pid,reviewer='reviewed')
    for i in range(20260010,20260013):
        ledger.seal(model_id='model-01',target_period=str(i),previous_period=str(i-1),
            candidates=['00000'],history_sha256='a'*64,source_description='official:test')
    ledger.settle(target_period='20260011',number='00000',source_description='official:test',data_sha256='b'*64)
    ledger.settle(target_period='20260012',number='00000',source_description='official:test',data_sha256='c'*64)
    r=ledger.model_report('model-01')
    assert r['verified_prefix']==0 and not r['evidence_threshold_crossed']
    assert r['pending_or_after_gap']==3


def test_anytime_lr_under_null_math():
    a=log_e_value([{'k':100,'hit':0} for _ in range(20)])
    b=log_e_value([{'k':100,'hit':1} for _ in range(20)])
    assert a['e_value']<1 and b['log_e']>0
    assert log_e_value([])['e_value']==pytest.approx(1)


def test_demo_smoke():
    d=demo()
    assert d['demo_only'] and not d['official_data_used']
    assert d['family']['models_registered']==2
    assert d['family']['models'][0]['total_commits']==20
    assert len(d['cross_checks'])==2


def test_pair_review_end_to_end_mock(ready):
    from autoresearch.pair_review_v09 import PairReview
    db,reg,ledger,cid,pid=ready
    lab=PythonResearchStore(db)
    other=lab.add(document_key='p',source=TRANSITION_SOURCE,origin='offline_template',
            method_claim='这是第二份独立设计的实验代码，尚未验证真实预测优势。')['code_id']
    pairs=PairReview(db)
    p=pairs.register(protocol_id=pid,primary_sha256=cid,reference_sha256=other,
        reviewer='human',independence_basis='两名不同作者独立编写的代码，已人工检查未共享模型参数逻辑。')
    assert p['code_digests_differ'] and p['independence_verified'] is False
    def fake_runner(source,cases):
        return {'ranked':[[f'{i:05d}' for i in range(3)] for _ in cases]}
    report=pairs.audit(p['pair_id'],['12345']*40,k=3,eval_size=2,runner=fake_runner)
    assert report['ranking_level_cross_reproduction']
    assert not report['faithful_paper_reproduction']
    with pytest.raises(ValueError,match='重复筛选'):
        pairs.audit(p['pair_id'],['12345']*40,k=3,eval_size=2,runner=fake_runner)


def test_pair_rejects_identical_code(ready):
    from autoresearch.pair_review_v09 import PairReview
    db,reg,ledger,cid,pid=ready
    with pytest.raises(ValueError,match='不同'):
        PairReview(db).register(protocol_id=pid,primary_sha256=cid,reference_sha256=cid,
         reviewer='human',independence_basis='已核对作者、代码结构与方法来源确实相互独立。')
