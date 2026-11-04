"""V1.5.1 read-only integration health dashboard. No prediction, data mutation, or auto approval.

All fields are diagnostics. A matching official URL is *not* cryptographic origin attestation.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import sqlite3

from snapshot_v15 import extract

SCHEMA = 'pl5-live-status-v151'


def _verify_ledger(db):
    previous = '0' * 64
    for row in db.execute('SELECT prev_sha256,event_json,event_sha256 FROM events ORDER BY seq'):
        if row['prev_sha256'] != previous or sha256((previous+row['event_json']).encode()).hexdigest() != row['event_sha256']:
            return False
        previous = row['event_sha256']
    return True


def _table(db, table):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _registry(path):
    result = {'state':'not_configured', 'ledger_verified':None,
              'counts':{'candidate':0,'experiment_reviewed':0,'approved_experimental':0,'revoked':0},
              'paused':0, 'scans':0, 'last_scan':None}
    if not path:
        return result
    p=Path(path)
    if not p.is_file():
        return {**result,'state':'file_missing'}
    # SQLite read-only URI. Do not implicitly initialize or alter an existing database.
    try:
        db=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
        db.row_factory=sqlite3.Row
        try:
            if not _table(db,'candidates') or not _table(db,'events'):
                return {**result,'state':'invalid_schema'}
            result['ledger_verified']=_verify_ledger(db)
            rows=db.execute('SELECT state, COUNT(*) AS n FROM candidates GROUP BY state')
            for row in rows:
                if row['state'] in result['counts']:result['counts'][row['state']]=int(row['n'])
            if _table(db,'v15_pauses'):
                result['paused']=int(db.execute('SELECT COUNT(*) FROM v15_pauses WHERE cleared_at IS NULL').fetchone()[0])
            if _table(db,'v15_scans'):
                result['scans']=int(db.execute('SELECT COUNT(*) FROM v15_scans').fetchone()[0])
                last=db.execute('SELECT id, report_json, created_at FROM v15_scans ORDER BY created_at DESC, rowid DESC LIMIT 1').fetchone()
                if last:
                    report=json.loads(last['report_json'])
                    entries=report.get('entries',[])
                    result['last_scan']={
                        'id':last['id'], 'created_at':last['created_at'],
                        'latest_issue':str(report.get('latest_issue',''))[:20],
                        'candidate_count':int(report.get('candidate_count',0)),
                        'failure_count':len(report.get('failures',[])),
                        'entries':[{'id':str(x.get('id',''))[:64], 'title':str(x.get('title',''))[:100],
                                    'state':str(x.get('state',''))[:40],
                                    'removed_fraction':float(x.get('removed_fraction',0)),
                                    'observed_removed_hits':int(x.get('observed_removed_hits',0)),
                                    'holdout_periods':int(x.get('holdout_periods',0)),
                                    'failure_signal':bool(x.get('failure_signal',False))}
                                   for x in entries[:30]]}
            result['state']='ready' if result['ledger_verified'] else 'ledger_invalid'
            return result
        finally: db.close()
    except (sqlite3.Error,ValueError,TypeError,KeyError,json.JSONDecodeError):
        return {**result,'state':'read_error'}


def _official_cache(path):
    result={'state':'not_configured','record_count':0,'latest_issue':None,'latest_date':None,
            'updated_at':None,'origin_cryptographically_verified':False}
    if not path:return result
    p=Path(path)
    if not p.is_file():return {**result,'state':'file_missing'}
    try:
        if p.stat().st_size>5_000_000:return {**result,'state':'oversize'}
        cache=json.loads(p.read_text(encoding='utf-8'))
        rows=extract(cache)
        result.update(state='fresh_structurally_valid',record_count=len(rows),
                      latest_issue=rows[-1]['issue'],latest_date=rows[-1]['date'],
                      updated_at=cache.get('updatedAt'))
    except (ValueError,TypeError,KeyError,OSError,json.JSONDecodeError):
        result['state']='invalid_or_stale'
    return result


def forward_summary(path):
    """Lightweight read-only status of prospective evidence."""
    result={'state':'not_configured','seals':0,'settled':0,'pending':0,
            'ledger_verified':None,'last_issue':None,'hits_in_prefix':0,
            'expected_fair_hits_in_prefix':0,'knife_actuals_in_prefix':{}}
    if not path:return result
    p=Path(path)
    if not p.is_file():return {**result,'state':'file_missing'}
    try:
        db=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
        db.row_factory=sqlite3.Row
        try:
            if not all(_table(db,t) for t in ('seals','settlements','evidence_events')):
                return {**result,'state':'invalid_schema'}
            prev='0'*64;ok=True
            for row in db.execute('SELECT prev_sha256,payload_json,event_sha256 FROM evidence_events ORDER BY seq'):
                expected=sha256((prev+row['payload_json']).encode()).hexdigest()
                if expected!=row['event_sha256'] or row['prev_sha256']!=prev:ok=False
                prev=row['event_sha256']
            rows=db.execute('SELECT s.target_issue,s.receipt_json,s.receipt_sha256,z.result_json,z.result_sha256 FROM seals s LEFT JOIN settlements z ON s.target_issue=z.target_issue ORDER BY CAST(s.target_issue AS INTEGER)').fetchall()
            event_count=db.execute('SELECT COUNT(*) FROM evidence_events').fetchone()[0]
            settled_count=db.execute('SELECT COUNT(*) FROM settlements').fetchone()[0]
            if event_count!=len(rows)+settled_count:ok=False
            entries=[]
            for row in rows:
                receipt=json.loads(row['receipt_json']); settlement=json.loads(row['result_json']) if row['result_json'] else None
                if sha256(json.dumps(receipt,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()!=row['receipt_sha256']:ok=False
                if settlement and sha256(json.dumps(settlement,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()!=row['result_sha256']:ok=False
                entries.append((receipt,settlement))
            prefix=[]
            for receipt,outcome in entries:
                if outcome is None:break
                prefix.append((receipt,outcome))
            kn={}
            for _,outcome in prefix:
                for d in outcome.get('knife_decisions',[]):
                    v=kn.setdefault(d['key'],{'would_cut_actual':0,'first_cut_actual':0})
                    v['would_cut_actual']+=int(d['would_cut']);v['first_cut_actual']+=int(d['first_cut'])
            return {**result,'state':'ready' if ok else 'ledger_invalid','ledger_verified':ok,
                    'seals':len(entries),'settled':sum(x[1] is not None for x in entries),
                    'pending':sum(x[1] is None for x in entries),
                    'last_issue':entries[-1][0]['target_issue'] if entries else None,
                    'auditable_prefix':len(prefix),
                    'hits_in_prefix':sum(v['is_hit'] for _,v in prefix),
                    'expected_fair_hits_in_prefix':sum(r['fair_probability'] for r,_ in prefix),
                    'knife_actuals_in_prefix':kn}
        finally:db.close()
    except (OSError,sqlite3.Error,ValueError,TypeError,KeyError,json.JSONDecodeError):
        return {**result,'state':'read_error'}




def _v17_read_status():
    import os
    from autoresearch.status_v17 import status as autonomous_status
    return autonomous_status(os.environ.get('PL5_V17_SUPERVISOR_DB'),
                             os.environ.get('PL5_V17_OFFICIAL_ARCHIVE'))

def status(*,registry_path=None,official_cache_path=None,forward_db_path=None):
    from pailie5.value_center_v16 import analyze as value_analysis
    return {
        'schema':SCHEMA,
        'generated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'bridge':{'state':'online','read_only':True},
        'registry':_registry(registry_path),
        'official_cache':_official_cache(official_cache_path),
        'forward_evidence':forward_summary(forward_db_path),
        'value_center':value_analysis(forward_db_path),
        'autonomous_research': _v17_read_status(),
        'safe_modes':{'auto_purchase':False,'auto_approval':False,
                      'research_scores_are_win_probabilities':False},
        'notice':'只报告本地系统状态；数据结构和官方URL标记不等于外部真实性认证；规则压缩不能证明提高中奖概率。'
    }
