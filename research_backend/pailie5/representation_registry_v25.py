"""V2.5 persistent autonomous engineering-idea inventory; no predictive publishing.

Each cycle uses a bounded mathematical operator generator. It never fetches
untrusted code, submits bets, retrains on held-out results, or enables a knife.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3

from .representation_v25 import audit, propose


def init(db: sqlite3.Connection) -> None:
    db.executescript('''
    CREATE TABLE IF NOT EXISTS representation_ideas (
      id TEXT PRIMARY KEY, partition_sha256 TEXT NOT NULL UNIQUE,
      capability_json TEXT NOT NULL, created_utc TEXT NOT NULL,
      status TEXT NOT NULL CHECK(status='engineering_research')
    );
    CREATE TABLE IF NOT EXISTS representation_cycles (
      id INTEGER PRIMARY KEY AUTOINCREMENT, seed INTEGER NOT NULL,
      created_utc TEXT NOT NULL, proposed INTEGER NOT NULL,
      within_cycle_accepted INTEGER NOT NULL, newly_registered INTEGER NOT NULL,
      summary_json TEXT NOT NULL
    );
    ''')


def cycle(db_path: str | Path, *, base_seed: int=20261102, count: int=24) -> dict:
    if not isinstance(base_seed,int) or isinstance(base_seed,bool) or not 0<=base_seed<2**32:
        raise ValueError('种子必须是32位非负整数')
    if not isinstance(count,int) or isinstance(count,bool) or not 1<=count<=60:
        raise ValueError('数量必须是1..60')
    path=Path(db_path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path,timeout=15) as db:
        init(db)
        db.execute('BEGIN IMMEDIATE')
        prior=db.execute('SELECT COUNT(*) FROM representation_cycles').fetchone()[0]
        seed=(base_seed+prior*7919)%(2**32)
        result=audit(propose(seed,count))
        now=datetime.now(timezone.utc).isoformat()
        new=[];duplicate=[]
        for row in result['reviewed']:
            if row['status']!='engineering_candidate':continue
            before=db.total_changes
            db.execute('INSERT OR IGNORE INTO representation_ideas (id,partition_sha256,capability_json,created_utc,status) VALUES(?,?,?,?,?)',
                       (row['id'],row['partition_sha256'],json.dumps(row['capability'],ensure_ascii=False,sort_keys=True),now,'engineering_research'))
            if db.total_changes>before:new.append(row['id'])
            else:duplicate.append(row['id'])
        summary={'version':'representation-cycle-v25','seed':seed,'generated':len(result['reviewed']),
                 'engineering_candidate_this_cycle':result['accepted'],
                 'newly_registered':len(new),'novel_ids':new,
                 'already_known_partitions':duplicate,
                 'reviewed_duplicate_or_relabelled':result['rejected'],
                 'prediction_advantage':'unverified','active_for_filtering':False,
                 'information':'仅研究能力资产。正式过滤需要独立验证与人工审批。'}
        db.execute('INSERT INTO representation_cycles(seed,created_utc,proposed,within_cycle_accepted,newly_registered,summary_json) VALUES(?,?,?,?,?,?)',
                   (seed,now,len(result['reviewed']),result['accepted'],len(new),json.dumps(summary,ensure_ascii=False,sort_keys=True)))
        db.commit()
        summary['registered_total']=db.execute('SELECT COUNT(*) FROM representation_ideas').fetchone()[0]
        summary['total_cycles']=prior+1
        return summary


def status(db_path: str | Path) -> dict:
    path=Path(db_path)
    if not path.exists():return {'status':'not_initialized','registered_total':0,'cycles':0}
    with sqlite3.connect(path) as db:
        init(db)
        n=db.execute('SELECT COUNT(*) FROM representation_ideas').fetchone()[0]
        c=db.execute('SELECT COUNT(*) FROM representation_cycles').fetchone()[0]
        latest=db.execute('SELECT summary_json FROM representation_cycles ORDER BY id DESC LIMIT 1').fetchone()
    return {'status':'engineering_research','registered_total':n,'cycles':c,
            'last_cycle':json.loads(latest[0]) if latest else None,'auto_promotion':False}
