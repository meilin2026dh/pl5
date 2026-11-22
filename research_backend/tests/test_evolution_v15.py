from datetime import date, timedelta
from hashlib import sha256
from unittest.mock import patch

import numpy as np
import pytest

from pailie5.algorithm_registry_v14 import Registry
from pailie5.integration_bridge import run_bridge, encode_mask, SCHEMA, ContractError
from pailie5.evolution_v15 import EvolutionLab, Policy, digest, validate_draws
from autoresearch.formulas import InventedAlgorithm

N=100000

def fixtures(n=40, *, base_date=date(2026,10,21), first_zero=False):
    return [{'issue':str(27000+i), 'date':(base_date+timedelta(days=i)).isoformat(),
            'number':f'{(i*7183+10000)%N:05d}' if not first_zero else f'0{i%10000:04d}'} for i in range(n)]

def proposed(db):
    mask=np.zeros(N,dtype=bool);mask[:10000]=True
    x=db.register(title='head zero',family='digit',creator='research-agent',
                  source_ref='local:fixture',cutoff_issue='26999',cutoff_date='2026-10-20',
                  data_sha256=sha256(b'fixture').hexdigest(),excluded=mask)
    return x['id']

def approved(db):
    k=proposed(db)
    out=db.evaluate_holdout(k,fixtures(11),snapshot_sha256=sha256(b'holdout').hexdigest())
    db.approve_experimental(k,experiment_id=out['experiment_id'],reviewer='human',
        consent='APPROVE_EXPERIMENTAL_NOT_PREDICTIVE')
    return k

def req(k):
    base=np.ones(N,dtype=bool)
    return {'schema':SCHEMA,'combination':'strict','base':encode_mask(base),
            'rules':[],'expected_strict_keep':N,'strict_kept':encode_mask(base),
            'k':20,'seed':13,'protocol_upgrade':'v13_verified',
            'meta':{'reference_issue':'26999'},'registered_rule_ids':[k]}

def test_reject_corrupt_and_duplicate_history():
    with pytest.raises(ValueError):validate_draws([{'issue':'1','date':'2026-11-01','number':23}])
    rows=fixtures(2);rows[1]['issue']=rows[0]['issue']
    with pytest.raises(ValueError):validate_draws(rows)
    with pytest.raises(ValueError):Policy(min_forward_periods=3)

def test_competition_correctness_replay_and_holdout(tmp_path):
    db=Registry(tmp_path/'x.sqlite'); k=approved(db); lab=EvolutionLab(db)
    d=fixtures(40,first_zero=True)
    report=lab.scan(d,source_label='official:unverified local test snapshot',reference_issue='27039')
    row=report['entries'][0]
    assert row['id']==k and row['removed_total']==10000
    assert row['holdout_periods']==40 and row['observed_removed_hits']==40
    assert row['marginal_removed']==10000 and row['overlap_with_other_approved']==0
    assert row['fair_expected_removed']==pytest.approx(4) and row['failure_signal']
    again=lab.scan(d,source_label='official:unverified local test snapshot',reference_issue='27039')
    assert again['replayed'] and again['id']==report['id']
    assert db.db.execute('SELECT COUNT(*) FROM v15_scans').fetchone()[0]==1
    assert not lab.paused(k)
    assert db.verify_ledger()
    db.close()

def test_auto_pause_blocks_bridge_until_explicit_review(tmp_path):
    db=Registry(tmp_path/'x.sqlite'); k=approved(db); lab=EvolutionLab(db)
    assert run_bridge(req(k),registry=db)['registered_rule_count']==1
    report=lab.scan(fixtures(40,first_zero=True),source_label='official:local test fixture',auto_pause=True)
    assert report['failures']==[k] and lab.paused(k)
    with pytest.raises(ContractError):run_bridge(req(k),registry=db)
    again=lab.scan(fixtures(40,first_zero=True),source_label='official:local test fixture',auto_pause=True)
    assert not again['failures'] and lab.paused(k)  # suspended state creates a new health snapshot
    again2=lab.scan(fixtures(40,first_zero=True),source_label='official:local test fixture',auto_pause=True)
    assert again2['replayed'] and lab.paused(k)
    with pytest.raises(ValueError):lab.resume(k,reviewer='x',explanation='short')
    lab.resume(k,reviewer='human-auditor',explanation='已核验测试数据和解释条件')
    assert run_bridge(req(k),registry=db)['registered_rule_count']==1
    # Replaying old evidence after explicit human resume must not undo the decision.
    lab.scan(fixtures(40,first_zero=True),source_label='official:local test fixture',auto_pause=True)
    assert not lab.paused(k)
    assert db.verify_ledger()
    db.close()

def test_no_approval_from_positive_score_and_expiry_report(tmp_path):
    db=Registry(tmp_path/'x.sqlite'); k=proposed(db); lab=EvolutionLab(db)
    r=lab.scan(fixtures(35),source_label='official:fixture',reference_issue='27099',auto_pause=True)
    assert r['entries'][0]['expired_for_reference']
    assert not r['entries'][0]['eligible_for_risk_decision']
    assert db.get(k)['state']=='candidate' and not lab.paused(k)
    db.close()

def test_source_domain_separation(tmp_path):
    db=Registry(tmp_path/'x.sqlite'); k=approved(db); lab=EvolutionLab(db)
    base=np.zeros(N,dtype=bool);base[:400]=True
    r=lab.scan(fixtures(40),source_label='official:fixture',source_mask=base)
    assert r['candidate_count']==0
    db.close()

def test_safe_auto_invention_no_promotion(tmp_path):
    db=Registry(tmp_path/'x.sqlite');lab=EvolutionLab(db)
    rows=fixtures(25,first_zero=True)
    algo=InventedAlgorithm({'kind':'metric','name':'digit_1'},'constant',3,'paper:test','safe')
    with patch('autoresearch.novelty_v07.invent_diverse',return_value=([algo],{'evaluated':1,'accepted':1})):
        r=lab.propose_from_text(text='time series',source_key='paper:test',history=rows,
                data_sha256=digest(rows),creator='agent',source_ref='paper:test')
    item=r['proposals'][0]
    assert item['status']=='registered_candidate' and item['excluded']==10000
    assert db.get(item['id'])['state']=='candidate'
    with pytest.raises(PermissionError):db.mask(item['id'])
    with pytest.raises(ValueError):lab.propose_from_text(text='test',source_key='x',history=rows,
        data_sha256='0'*64,creator='agent',source_ref='x')
    db.close()
