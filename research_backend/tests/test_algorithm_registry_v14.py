from datetime import date,timedelta
import hashlib
import json
import sqlite3

import numpy as np
import pytest
from pailie5.algorithm_registry_v14 import Registry, from_github_rule
from pailie5.integration_bridge import SCHEMA, encode_mask, run_bridge, ContractError

N=100000
CUT='2026-10-20'

def digest(s='history'): return hashlib.sha256(s.encode()).hexdigest()

def draw_rows(n=15):
    start=date(2026,10,21)
    return [{'issue':str(26300+i),'date':(start+timedelta(days=i)).isoformat(),
             'number':f'{(i*1947+1)%100000:05d}'} for i in range(n)]

def mask():
    a=np.zeros(N,dtype=bool);a[:10000]=True;return a

def proposal(db,*,source=None):
    return db.register(title='first-position-zero',family='position',creator='agent',
       source_ref='github:src/domain/pick5.ts#rule',cutoff_issue='26290',cutoff_date=CUT,
       data_sha256=digest(),excluded=mask(),source_mask=source)

def bridge_req(*,base=None,registered=None,reference='26290'):
    if base is None:base=np.ones(N,dtype=bool)
    return {'schema':SCHEMA,'combination':'strict','k':20,'seed':123,
       'base':encode_mask(base),'rules':[], 'expected_strict_keep':int(base.sum()),
       'strict_kept':encode_mask(base),'protocol_upgrade':'v13_verified',
       'meta':{'reference_issue':reference,'history_source':'fixture'},
       'registered_rule_ids': registered if registered is not None else []}

def approve(db):
    key=proposal(db)['id']; result=db.evaluate_holdout(key,draw_rows(),snapshot_sha256=digest('future'))
    db.approve_experimental(key,experiment_id=result['experiment_id'],reviewer='human-auditor',
                            consent='APPROVE_EXPERIMENTAL_NOT_PREDICTIVE')
    return key,result

def test_candidate_register_and_mask_integrity(tmp_path):
    db=Registry(tmp_path/'reg.sqlite')
    x=proposal(db);assert x['new']
    assert proposal(db)['new'] is False
    assert int(db.mask(x['id'],require_approval=False).sum())==10000
    with pytest.raises(PermissionError):db.mask(x['id'])
    assert db.verify_ledger()
    db.close()

def test_cannot_approve_without_valid_frozen_experiment(tmp_path):
    db=Registry(tmp_path/'reg.sqlite');key=proposal(db)['id']
    with pytest.raises(PermissionError):db.approve_experimental(key,experiment_id=1,reviewer='auditor',consent='APPROVE_EXPERIMENTAL_NOT_PREDICTIVE')
    with pytest.raises(ValueError):db.evaluate_holdout(key,draw_rows(9),snapshot_sha256=digest('t'))
    wrong=draw_rows();wrong[0]['date']=CUT
    with pytest.raises(ValueError):db.evaluate_holdout(key,wrong,snapshot_sha256=digest('t'))
    a=db.evaluate_holdout(key,draw_rows(),snapshot_sha256=digest('t'))
    assert a['periods']==15
    with pytest.raises(PermissionError):db.approve_experimental(key,experiment_id=a['experiment_id'],reviewer='agent',consent='APPROVE_EXPERIMENTAL_NOT_PREDICTIVE')
    with pytest.raises(PermissionError):db.approve_experimental(key,experiment_id=a['experiment_id'],reviewer='auditor',consent='wrong')
    assert db.approve_experimental(key,experiment_id=a['experiment_id'],reviewer='auditor',consent='APPROVE_EXPERIMENTAL_NOT_PREDICTIVE')['prediction_validated'] is False
    assert db.verify_ledger()
    db.close()

def test_bridge_refuses_self_asserted_registered_rule_and_applies_reviewed_only(tmp_path):
    db=Registry(tmp_path/'reg.sqlite');key=proposal(db)['id']
    with pytest.raises(ContractError):run_bridge(bridge_req(registered=[key]))
    with pytest.raises(ContractError):run_bridge(bridge_req(registered=[key]),registry=db)
    audit=db.evaluate_holdout(key,draw_rows(),snapshot_sha256=digest('future'))
    db.approve_experimental(key,experiment_id=audit['experiment_id'],reviewer='human',
                            consent='APPROVE_EXPERIMENTAL_NOT_PREDICTIVE')
    result=run_bridge(bridge_req(registered=[key]),registry=db)
    assert result['typescript_strict_keep_count']==100000
    assert result['strict_keep_count']==90000
    assert result['registered_rule_count']==1
    assert result['registered_rules_are_predictive'] is False
    assert result['source_guard']
    assert all(not x.startswith('0') for x in result['top_numbers'])
    with pytest.raises(ContractError):run_bridge(bridge_req(registered=[key],reference='26291'),registry=db)
    db.revoke(key,reviewer='human',reason='retired')
    with pytest.raises(ContractError):run_bridge(bridge_req(registered=[key]),registry=db)
    db.close()

def test_source_domain_guard_and_github_import(tmp_path):
    db=Registry(tmp_path/'reg.sqlite');base=np.zeros(N,dtype=bool);base[:12000]=True
    keep=base.copy();keep[:2000]=False
    req=bridge_req(base=base)
    item={'id':'github-rule','label':'some-advanced','group':'math','enabled':True,'kept':encode_mask(keep)}
    x=from_github_rule(req,item,creator='agent',cutoff_date=CUT,source_ref='github/test',
                       data_sha256=digest(),registry=db)
    result=db.evaluate_holdout(x['id'],draw_rows(),snapshot_sha256=digest('future'))
    db.approve_experimental(x['id'],experiment_id=result['experiment_id'],reviewer='human',consent='APPROVE_EXPERIMENTAL_NOT_PREDICTIVE')
    worked=run_bridge(bridge_req(base=base,registered=[x['id']]),registry=db)
    assert worked['strict_keep_count']==10000
    with pytest.raises(ContractError):run_bridge(bridge_req(registered=[x['id']]),registry=db)
    db.close()

def test_ledger_corruption_detected(tmp_path):
    db=Registry(tmp_path/'reg.sqlite');key,_=approve(db)
    db.db.execute('UPDATE events SET event_json=? WHERE seq=1',('{"tampered":true}',))
    db.db.commit()
    assert not db.verify_ledger()
    with pytest.raises(ContractError):run_bridge(bridge_req(registered=[key]),registry=db)
    db.close()

def test_empty_or_full_masks_rejected(tmp_path):
    db=Registry(tmp_path/'reg.sqlite')
    for a in (np.zeros(N,dtype=bool),np.ones(N,dtype=bool)):
        with pytest.raises(ValueError):db.register(title='x',family='x',creator='x',source_ref='x',cutoff_issue='26290',cutoff_date=CUT,data_sha256=digest(),excluded=a)
    db.close()

def test_no_code_execution_in_registry(tmp_path):
    db=Registry(tmp_path/'reg.sqlite')
    a=proposal(db)
    assert 'mask_sha256' in db.get(a['id'])
    tables={r['name'] for r in db.db.execute("select name from sqlite_master where type='table'")}
    assert 'candidates' in tables and 'reviews' in tables and 'events' in tables
    db.close()


def test_user_supplied_fake_approval_has_no_effect(tmp_path):
    db=Registry(tmp_path/'r.sqlite');key=proposal(db)['id']
    req=bridge_req(registered=[key]);req['approval']='approved';req['registry_status']='approved_experimental'
    with pytest.raises(ContractError): run_bridge(req,registry=db)
    db.close()
