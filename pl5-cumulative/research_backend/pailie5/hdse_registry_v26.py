"""Research-only append-only HDSE capability registry. No automatic predictive promotion."""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime,timezone
from pathlib import Path
from .highdim_v26 import proposals


def _connect(path:Path)->sqlite3.Connection:
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=10)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS hdse_cycles (id INTEGER PRIMARY KEY, created TEXT NOT NULL, seed INTEGER NOT NULL, attempted INTEGER NOT NULL, inserted INTEGER NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS hdse_capabilities (id TEXT PRIMARY KEY, created TEXT NOT NULL, cycle INTEGER NOT NULL, card_json TEXT NOT NULL)')
    return db


def grow(path:Path, *, base_seed:int=20261102, maximum:int=12)->dict:
    if type(base_seed) is not int or not 0<=base_seed<2**32:raise ValueError('base_seed非法')
    if type(maximum) is not int or not 1<=maximum<=12:raise ValueError('maximum必须在1—12')
    with _connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        cycle=db.execute('SELECT COALESCE(MAX(id),0)+1 FROM hdse_cycles').fetchone()[0]
        seed=(base_seed+cycle*104729)%(2**32)
        items=proposals(seed,maximum)
        timestamp=datetime.now(timezone.utc).isoformat()
        inserted=0
        for spec in items:
            card=spec.capability()
            cur=db.execute('INSERT OR IGNORE INTO hdse_capabilities(id,created,cycle,card_json) VALUES (?,?,?,?)',
                (spec.id,timestamp,cycle,json.dumps(card,ensure_ascii=False,sort_keys=True)))
            inserted+=cur.rowcount
        db.execute('INSERT INTO hdse_cycles(id,created,seed,attempted,inserted) VALUES (?,?,?,?,?)',
                   (cycle,timestamp,seed,len(items),inserted))
        total=db.execute('SELECT COUNT(*) FROM hdse_capabilities').fetchone()[0]
    return {'version':'hdse-v26','cycle':cycle,'seed':seed,'attempted':len(items),
            'new_capabilities':inserted,'registered_total':total,
            'status':'research_capabilities_only','automatic_predictive_promotion':False,
            'capacity_note':'当前3个有界模型家族共有44种非伪参数配置；增量终会饱和。'}


def status(path:Path)->dict:
    path=Path(path)
    if not path.exists():return {'version':'hdse-v26','status':'not_initialized','registered_total':0,'cycles':0}
    with _connect(path) as db:
        total=db.execute('SELECT COUNT(*) FROM hdse_capabilities').fetchone()[0]
        cycles=db.execute('SELECT COUNT(*) FROM hdse_cycles').fetchone()[0]
        recent=db.execute('SELECT id,created,cycle,card_json FROM hdse_capabilities ORDER BY rowid DESC LIMIT 12').fetchall()
    return {'version':'hdse-v26','status':'research_capabilities_only',
            'registered_total':total,'cycles':cycles,
            'recent':[{'id':id,'created':created,'cycle':cycle,'card':json.loads(card)} for id,created,cycle,card in recent],
            'automatic_predictive_promotion':False}
