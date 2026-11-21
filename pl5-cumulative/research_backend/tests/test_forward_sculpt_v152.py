import copy
import json
import sqlite3
from datetime import datetime, timedelta, timezone
import numpy as np
import pytest
from pailie5.forward_sculpt_v152 import SculptLedger, digest
from pailie5.integration_bridge import encode_mask,SCHEMA
from snapshot_v15 import extract, OFFICIAL_URL


def mk_mask(a,b):
    z=np.zeros(100000,dtype=bool);z[a:b]=True
    return encode_mask(z)


def request(cutoff='26290'):
    return {'schema':SCHEMA,'combination':'strict','k':100,'seed':123,
      'base':mk_mask(100,600),'rules':[
        {'id':'a','label':'A','group':'a','enabled':True,'kept':mk_mask(100,450)},
        {'id':'b','label':'B','group':'b','enabled':True,'kept':mk_mask(200,600)}],
      'expected_strict_keep':250,'meta':{'reference_issue':cutoff,'history_source':'官方历史接口测试模拟'}}


def rows():
    return [{'issue':'26289','date':'2026-10-30','number':'00100'},
            {'issue':'26290','date':'2026-10-31','number':'00200'}]


def seal(ledger,nums=None,req=None,target='26291'):
    return ledger.seal(target_issue=target, official_draws=nums or rows(),
                       source_label='test fixture only - official format',bridge_request=req or request(),
                       code_revision='test-sha')


def test_seal_and_settle_success_per_knife(tmp_path):
    with SculptLedger(tmp_path/'ledger.db') as ledger:
        receipt=seal(ledger)
        assert receipt['count']==100 and receipt['stages']==3
        assert ledger.verify()['ok']
        assert ledger.report()['pending']==1
        final=ledger.settle(official_draws=rows()+[{'issue':'26291','date':'2026-11-01','number':'00150'}],source_label='official style synthetic fixture')
        assert final['newly_settled']==1
        report=ledger.report()
        assert report['settled']==1 and report['hits_in_prefix']==0
        assert report['knife_actuals_in_prefix']['a']['would_cut_actual']==0
        assert report['knife_actuals_in_prefix']['b']['first_cut_actual']==1
        assert report['knife_actuals_in_prefix']['__source__']['first_cut_actual']==0
        assert report['integrity']['ok']
        assert ledger.settle(official_draws=rows()+[{'issue':'26291','date':'2026-11-01','number':'00150'}],source_label='fixture')['newly_settled']==0
        with pytest.raises(sqlite3.DatabaseError):ledger.db.execute('UPDATE settlements SET draw_number="99999"')
        with pytest.raises(sqlite3.DatabaseError):ledger.db.execute('DELETE FROM seals')


def test_no_backfill_future_known_duplicate(tmp_path):
    with SculptLedger(tmp_path/'ledger.db') as ledger:
        with pytest.raises(ValueError,match='事后封存'):
            seal(ledger, nums=rows()+[{'issue':'26291','date':'2026-11-01','number':'12345'}])
        with pytest.raises(ValueError,match='截止期'):
            seal(ledger,req=request('26289'))
        seal(ledger)
        with pytest.raises(ValueError,match="递增"):seal(ledger)
        with pytest.raises(ValueError,match='晚于'):
            seal(ledger,target='26280')


def test_tamper_detection_even_if_only_receipt_changed(tmp_path):
    with SculptLedger(tmp_path/'ledger.db') as ledger:
        seal(ledger)
        ledger.db.execute('DROP TRIGGER seals_no_update')
        ledger.db.execute('UPDATE seals SET history_sha256=?',('a'*64,))
        ledger.db.commit()
        assert not ledger.verify()['ok']
        with pytest.raises(PermissionError,match='异常'):seal(ledger,target='26292')


def test_revision_blocks_entire_settlement_batch(tmp_path):
    with SculptLedger(tmp_path/'ledger.db') as ledger:
        seal(ledger)
        changed=copy.deepcopy(rows());changed[0]['number']='00999'
        with pytest.raises(ValueError,match='发生变化'):
            ledger.settle(official_draws=changed+[{'issue':'26291','date':'2026-11-01','number':'00200'}],source_label='fixture')
        assert ledger.report()['pending']==1


def test_minimal_cache_validation(tmp_path):
    cache={'sourceUrl':OFFICIAL_URL,'updatedAt':datetime.now(timezone.utc).isoformat(),
           'draws':rows()}
    assert len(extract(cache))==2
    cache['stale']=True
    with pytest.raises(ValueError):extract(cache)


def test_report_pending_blocks_later_score(tmp_path):
    with SculptLedger(tmp_path/'ledger.db') as ledger:
        seal(ledger)
        newer=rows()+[{'issue':'26291','date':'2026-11-01','number':'00110'}]
        seal(ledger,nums=newer,req=request('26291'),target='26292')
        # no target 26291 settlement, but 26292 known to this upload
        result=ledger.settle(official_draws=newer+[{'issue':'26292','date':'2026-11-02','number':'00220'}],source_label='fixture')
        assert result['newly_settled']==2  # both present: complete series
        r=ledger.report();assert r['auditable_settled_prefix']==2
        assert r['rolling_10_registered']==[]


def test_readonly_status_reports_evidence(tmp_path):
    from status_v151 import forward_summary, status
    database=tmp_path/'evidence.sqlite'
    assert forward_summary(database)['state']=='file_missing'
    assert not database.exists()
    with SculptLedger(database) as ledger:
        seal(ledger)
        ledger.settle(official_draws=rows()+[{'issue':'26291','date':'2026-11-01','number':'00150'}],source_label='fixture')
    s=forward_summary(database)
    assert s['state']=='ready' and s['ledger_verified']
    assert s['seals']==s['settled']==1
    assert s['knife_actuals_in_prefix']['b']['first_cut_actual']==1
    assert status(forward_db_path=database)['forward_evidence']['hits_in_prefix']==0


def test_settlement_revision_previously_settled_detected(tmp_path):
    with SculptLedger(tmp_path/'evidence.sqlite') as ledger:
        seal(ledger)
        dataset=rows()+[{'issue':'26291','date':'2026-11-01','number':'00150'}]
        ledger.settle(official_draws=dataset,source_label='fixture')
        dataset[-1]['number']='99999'
        with pytest.raises(ValueError,match='发生修改'):
            ledger.settle(official_draws=dataset,source_label='fixture')
