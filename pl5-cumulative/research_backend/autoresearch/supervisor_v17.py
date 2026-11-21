"""Durable autonomous *research*, never autonomous betting or algorithm approval.

One idempotent 6-hour cycle; every stage persists state before proceeding.
The existing v10 coordinator checkpoints each internal step. Crashes preserve
incomplete stages for explicit retry with the same frozen cycle config.
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import sqlite3
import time

from .integrated_v10 import ResearchCoordinator, sha
from .store import LabStore
from .official_archive_v17 import OfficialArchive


def utc():return datetime.now(timezone.utc).isoformat(timespec='seconds')

def cycle_now(now=None):
    dt=now or datetime.now(timezone.utc)
    if dt.tzinfo is None:raise ValueError('调度周期必须有时区')
    dt=dt.astimezone(timezone.utc)
    return dt.strftime('%Y%m%d')+f'-{dt.hour//6*6:02d}'


@contextmanager
def single_instance(lock_path):
    """OS-held lock, released automatically on process exit, cross-platform."""
    p=Path(lock_path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a+b') as f:
        f.seek(0);f.write(b'0');f.flush();f.seek(0)
        if os.name=='nt':
            import msvcrt
            try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            except OSError:raise RuntimeError('已有V1.7科研任务正在运行') from None
            try:yield
            finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise RuntimeError('已有V1.7科研任务正在运行') from None
            try:yield
            finally:fcntl.flock(f.fileno(),fcntl.LOCK_UN)


class Supervisor:
    def __init__(self, db_path, archive_root, research_db):
        self.db_path=Path(db_path)
        self.db_path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.db_path,timeout=10)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA busy_timeout=10000')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS v17_cycles(
          cycle_key TEXT PRIMARY KEY, config TEXT NOT NULL, config_sha256 TEXT NOT NULL,
          state TEXT NOT NULL, started_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          last_error TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS v17_stages(
          cycle_key TEXT NOT NULL, stage TEXT NOT NULL,
          status TEXT NOT NULL, attempts INTEGER NOT NULL,
          updated_at TEXT NOT NULL, result_json TEXT, result_sha256 TEXT,
          error TEXT NOT NULL DEFAULT '',PRIMARY KEY(cycle_key,stage));
        ''');self.db.commit()
        self.archive=OfficialArchive(archive_root)
        self.research_db=str(research_db)

    def close(self):self.db.close()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()

    def _start(self,key,cfg):
        sig=sha(cfg)
        prior=self.db.execute('SELECT config_sha256 FROM v17_cycles WHERE cycle_key=?',(key,)).fetchone()
        if prior and prior['config_sha256']!=sig:
            raise ValueError('同一周期的参数已封存，变更配置须等待下一周期或另用周期标识')
        if not prior:
            self.db.execute('INSERT INTO v17_cycles VALUES(?,?,?,?,?,?,?)',
                (key,json.dumps(cfg,ensure_ascii=False,sort_keys=True),sig,'pending',utc(),utc(),''))
            self.db.commit()

    def _stage(self,key,name,fn):
        r=self.db.execute('SELECT * FROM v17_stages WHERE cycle_key=? AND stage=?',(key,name)).fetchone()
        if r and r['status']=='done':
            result=json.loads(r['result_json'])
            if sha(result)!=r['result_sha256']:raise RuntimeError('阶段记录被篡改：'+name)
            return result
        attempts=(r['attempts'] if r else 0)+1
        self.db.execute('''INSERT INTO v17_stages(cycle_key,stage,status,attempts,updated_at)
          VALUES(?,?,?,?,?) ON CONFLICT(cycle_key,stage) DO UPDATE SET
          status='running', attempts=excluded.attempts, updated_at=excluded.updated_at,
          error='',result_json=NULL,result_sha256=NULL''',(key,name,'running',attempts,utc()))
        self.db.execute("UPDATE v17_cycles SET state='running',updated_at=?,last_error='' WHERE cycle_key=?",(utc(),key))
        self.db.commit()
        try:
            result=fn()
            payload=json.dumps(result,ensure_ascii=False,sort_keys=True,allow_nan=False)
            self.db.execute('UPDATE v17_stages SET status=?,updated_at=?,result_json=?,result_sha256=? WHERE cycle_key=? AND stage=?',
                            ('done',utc(),payload,sha(result),key,name))
            self.db.commit()
            return result
        except Exception as exc:
            err=f'{type(exc).__name__}: {exc}'[:400]
            self.db.execute('UPDATE v17_stages SET status=?,updated_at=?,error=? WHERE cycle_key=? AND stage=?',('failed',utc(),err,key,name))
            self.db.execute('UPDATE v17_cycles SET state=?,updated_at=?,last_error=? WHERE cycle_key=?',('failed',utc(),err,key))
            self.db.commit()
            raise

    def run(self,*,key,mode='offline',papers=None,sync_official=False,pages=2,
            topics=('sequential multiple testing','randomness testing'),providers=('openalex','arxiv'),
            audit=False, research_runner=None, archive_fetcher=None):
        if not isinstance(key,str) or len(key)>50 or not key or not all(c.isalnum() or c in '-_' for c in key):
            raise ValueError('周期标识不合法')
        if mode not in ('offline','live') or (mode=='offline' and papers is None):
            raise ValueError('离线周期必须提供文献样例；在线周期必须显式指定')
        if sync_official and mode!='live':raise ValueError('离线模式禁止联网同步')
        if audit and not sync_official and self.archive.status()['state']!='ready':
            raise ValueError('开发性回测需要已经保存的官方历史档案')
        cfg={'mode':mode,'fixture_sha256':sha([p.to_dict() for p in papers]) if papers is not None else None,
             'sync_official':bool(sync_official),'pages':int(pages), 'topics':list(topics),
             'providers':list(providers),'audit':bool(audit)}
        self._start(key,cfg)
        def syncing():
            if not sync_official:return {'state':'skipped','archive':self.archive.status()}
            try:
                archive=self.archive.sync(pages,fetcher=archive_fetcher) if archive_fetcher else self.archive.sync(pages)
                return {'state':'synced','archive':archive}
            except (OSError,TimeoutError,json.JSONDecodeError) as exc:
                # Temporary network outages must not prevent independent paper research.
                # The *current* official update is unavailable, so do not audit stale draws.
                return {'state':'network_unavailable','archive':self.archive.status(),
                        'notice':(type(exc).__name__+': '+str(exc))[:260],
                        'development_audit_blocked':True}
        src=self._stage(key,'official_sync',syncing)
        def researching():
            if research_runner:
                return research_runner(key, cfg, papers, self.archive)
            history=None;source=None
            effective_audit=audit and src['state']!='network_unavailable'
            if effective_audit:
                rows,meta=self.archive.load()
                if src['state']=='synced' and meta['version']!=src['archive']['version']:
                    # No silently moving to another snapshot after a crashed cycle.
                    raise ValueError('历史快照在科研阶段前发生变化，请检查独立运行任务')
                if len(rows)<60:raise ValueError('官方数据不足，停止开发性实验')
                history=[r['number'] for r in rows]
                source='official:'+str(meta['source'])
            with LabStore(self.research_db) as store:
                coord=ResearchCoordinator(store)
                research_cfg={'mode':mode,'topics':list(topics),'providers':list(providers),
                              'max_requests':12,'max_documents':3,
                              'enable_development_audit':effective_audit,
                              'dataset_sha256':sha(history) if history is not None else None,
                              'official_source':source}
                if mode=='offline':research_cfg['fixture']=sha([p.to_dict() for p in papers])
                frozen=coord.normalize_config(research_cfg)
                run_id='run_v17_'+sha([key,frozen])[:24]
                coord.create(research_cfg,run_id=run_id)
                output=coord.run(run_id,fixture_papers=papers,history_numbers=history)
                return {'run_id':run_id,'state':output['status'],
                        'steps':list(output['steps']),
                        'new_formulas':len(output['steps'].get('invent',{}).get('formulas',[])),
                        'no_auto_approval':True,'paid_calls':0,
                        'development_only':bool(effective_audit), 'official_sync_state':src['state']}
        research=self._stage(key,'research',researching)
        report=self._stage(key,'finalize',lambda:{'key':key,'mode':mode,'data':src,'research':research,
                      'publication':'candidate_only','autonomous_code_execution':False,
                      'automatic_approval':False,'predictive_advantage_proven':False})
        self.db.execute("UPDATE v17_cycles SET state='completed',updated_at=?,last_error='' WHERE cycle_key=?",(utc(),key))
        self.db.commit()
        return report

    def status(self,limit=12):
        cycles=[dict(x) for x in self.db.execute('SELECT * FROM v17_cycles ORDER BY started_at DESC LIMIT ?',(limit,))]
        for c in cycles:
            c['config']=json.loads(c.pop('config'));c['stages']=[]
            for row in self.db.execute('SELECT stage,status,attempts,updated_at,error FROM v17_stages WHERE cycle_key=? ORDER BY rowid',(c['cycle_key'],)):
                c['stages'].append(dict(row))
        return {'schema':'pl5-autonomous-v17','cycles':cycles,'archive':self.archive.status(),
                'unattended_paid_calls_enabled':False,'autonomous_approval_enabled':False}
