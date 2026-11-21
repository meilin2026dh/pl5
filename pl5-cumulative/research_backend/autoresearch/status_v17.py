"""Read-only status for the long-running research scheduler."""
from __future__ import annotations
from pathlib import Path
from urllib.parse import quote
import sqlite3
from .official_archive_v17 import OfficialArchive


def status(db_path=None,archive_root=None):
    result={'schema':'pl5-autonomous-status-v17','state':'not_configured',
            'last_cycle':None,'completed_cycles':0,'failed_cycles':0,
            'official_archive':{'state':'not_configured'},'paid_calls_enabled':False,
            'automatic_algorithm_approval':False}
    if archive_root:
        try:result['official_archive']=OfficialArchive(archive_root).status()
        except (ValueError, OSError, KeyError, TypeError):result['official_archive']={'state':'invalid_or_conflicted'}
    if not db_path:return result
    p=Path(db_path)
    if not p.is_file():return {**result,'state':'not_initialized'}
    try:
        db=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
        db.row_factory=sqlite3.Row
        try:
            present=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='v17_cycles'").fetchone()
            if not present:return {**result,'state':'invalid_schema'}
            rows=db.execute('SELECT cycle_key,state,started_at,updated_at,last_error FROM v17_cycles ORDER BY started_at DESC LIMIT 1').fetchall()
            counts=dict(db.execute('SELECT state,COUNT(*) FROM v17_cycles GROUP BY state').fetchall())
            result['completed_cycles']=counts.get('completed',0)
            result['failed_cycles']=counts.get('failed',0)
            if rows:
                x=dict(rows[0]);x['stages']=[dict(t) for t in db.execute('SELECT stage,status,attempts,updated_at,error FROM v17_stages WHERE cycle_key=? ORDER BY rowid',(x['cycle_key'],))]
                result['last_cycle']=x
            result['state']='ready'
            return result
        finally:db.close()
    except (sqlite3.Error,OSError):return {**result,'state':'read_error'}
